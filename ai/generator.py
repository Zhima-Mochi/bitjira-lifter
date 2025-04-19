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
device = accelerator.device

# Load local model and tokenizer
MODEL_PATH = os.getenv("LOCAL_LLM_PATH", "./models/llm")

# Safely load the model with error handling
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH)
    model.to(device)
    generator = pipeline("text-generation", model=model,
                         tokenizer=tokenizer, device=device)
    MODEL_LOADED = True
except Exception as e:
    logger.error(f"Error loading model: {e}")
    logger.warning("Falling back to placeholder text generation")
    MODEL_LOADED = False


def generate(prompt: str, max_new_tokens: int = 100, do_sample: bool = True, top_p: float = 0.95, temperature: float = 0.7) -> str:
    """Generate text using the loaded model or return a placeholder if model failed to load."""
    if not MODEL_LOADED:
        return f"[AI generation unavailable - placeholder for: {prompt[:30]}...]"

    try:
        output = generator(prompt, max_new_tokens=max_new_tokens,
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
