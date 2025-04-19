import os
from typing import Dict
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from accelerate import Accelerator
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    generator = pipeline("text-generation", model=model, tokenizer=tokenizer, device=device)
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
        output = generator(prompt, max_new_tokens=max_new_tokens, do_sample=do_sample, top_p=top_p, temperature=temperature)
        return output[0]["generated_text"].replace(prompt, "").strip()
    except Exception as e:
        logger.error(f"Error during text generation: {e}")
        return f"[Error during generation: {str(e)[:50]}...]"

def generate_commit_message(diff: str, ticket: str = None) -> str:
    """
    Call local Hugging Face model to create a commit message based on diff and optional ticket ref.
    """
    prompt = f"Generate a concise git commit message based on the following diff:\n{diff}"
    if ticket:
        prompt += f"\nInclude Jira ticket {ticket} in the footer."

    message = generate(prompt, max_new_tokens=100, do_sample=True, top_p=0.95, temperature=0.7)
    
    # Format according to PR template rules
    if ticket:
        # Add ticket reference in standard format [TICKET-ID]
        if not message.startswith(f"[{ticket}]"):
            message = f"[{ticket}] {message}"
    
    return message


def generate_pr_description(fields: Dict[str, str], template_path: str) -> str:
    """
    Fill the PR template with provided field values.
    """
    from utils.template_engine import apply_template
    template = apply_template(template_path, fields)
    
    prompt = f"Generate a PR description based on the following template:\n{template}"
    description = generate(prompt, max_new_tokens=100, do_sample=True, top_p=0.95, temperature=0.7)
    
    return description

def generate_summary(ticket: str) -> str:
    """
    Generate a summary for a ticket using the AI model.
    
    Args:
        ticket: The ticket ID to generate a summary for
        
    Returns:
        A generated summary string
    """
    # In a real implementation, this would fetch ticket details from Jira
    # For now, we'll generate a generic summary
    prompt = f"Generate a short, concise summary for Jira ticket {ticket}:"
    summary = generate(prompt, max_new_tokens=50)
    
    return summary
