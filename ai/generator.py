import os
from typing import Dict, Optional
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from accelerate import Accelerator
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize accelerator
accelerator = Accelerator()
DEVICE = accelerator.device

MODEL_LOADED = False
MODEL = None
TOKENIZER = None
GENERATOR = None

def prepare_model(model_id: str = None):
    """
    Load model from local path or HuggingFace (fallback).
    If LOCAL_LLM_PATH exists, loads from local dir.
    If not, auto-download from HuggingFace using `model_id`.
    """
    global MODEL_LOADED, MODEL, TOKENIZER, DEVICE
    if MODEL_LOADED:
        return
    
    model_id = model_id or os.getenv("MODEL_ID")
    if not model_id:
        raise ValueError("MODEL_ID environment variable is not set")

    try:
        TOKENIZER = AutoTokenizer.from_pretrained(model_id)
        MODEL = AutoModelForCausalLM.from_pretrained(model_id)
        MODEL.to(DEVICE)
        logger.info(f"Model loaded from {model_id}")
        MODEL_LOADED = True
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        MODEL_LOADED = False

def prepare_generator():
    global GENERATOR
    if GENERATOR:
        return
    prepare_model()
    if not MODEL_LOADED:
        return
    GENERATOR = pipeline("text-generation", model=MODEL, tokenizer=TOKENIZER, device=DEVICE)

def generate(prompt: str, max_new_tokens: int = 100, do_sample: bool = True, top_p: float = 0.95, temperature: float = 0.7) -> str:
    """Generate text using the loaded model or return a placeholder if model failed to load."""
    prepare_generator()
    if not MODEL_LOADED:
        return f"[AI generation unavailable - placeholder for: {prompt[:30]}...]"

    try:
        output = GENERATOR(prompt, max_new_tokens=max_new_tokens,
                           do_sample=do_sample, top_p=top_p, temperature=temperature)
        return output[0]["generated_text"].replace(prompt, "").strip()
    except Exception as e:
        logger.error(f"Error during text generation: {e}")
        return f"[Error during generation: {str(e)[:50]}...]"


def generate_with_prompt(prompt_template: str, context: Dict[str, str], **gen_kwargs) -> str:
    """
    Fill in prompt_template with context and generate text using local LLM.

    Args:
        prompt_template: A prompt string like "Summarize ticket {ticket}: {diff}"
        context: A dict with fields to replace in the prompt
        gen_kwargs: Optional generation parameters (max_new_tokens, temperature, etc.)

    Returns:
        Generated text (str)
    """
    prompt = prompt_template.format(**context)
    return generate(prompt, **gen_kwargs)


def generate_commit_message(diff: str, ticket: Optional[str] = None) -> str:
    """
    Generate a commit message based on diff and optionally a ticket reference.

    Args:
        diff: Git diff content
        ticket: Optional Jira ticket ID

    Returns:
        Generated commit message
    """
    prompt = f"Generate a clear and concise commit message for the following code changes:\n\n{diff[:5000]}"
    if ticket:
        prompt += f"\n\nInclude the reference to Jira ticket {ticket} in the message."

    message = generate(prompt, max_new_tokens=150)
    return message


def generate_pr_description(ticket: str, diff: str, template_path: Optional[str] = None) -> str:
    """
    Generate a pull request description directly using the ticket info and diff.

    Args:
        ticket: Jira ticket ID
        diff: Git diff content
        template_path: Path to the PR template file

    Returns:
        PR description based on template with AI-generated content
    """
    try:
        template = None
        # Read the template
        if template_path:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()

        # Generate summary
        description_prompt = f"Summarize the changes for ticket {ticket}:\n\n{diff[:5000]}"
        if template:
            description_prompt += f"\n\nThe description should be in the format of {template}"
        description = generate(description_prompt, max_new_tokens=150)
        return description
    except Exception as e:
        logger.error(f"Error generating PR description: {e}")
        return f"Failed to generate PR description: {str(e)}"
