import os
from typing import Dict
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from accelerate import Accelerator

accelerator = Accelerator()
device = accelerator.device

# Load local model and tokenizer
MODEL_PATH = os.getenv("LOCAL_LLM_PATH", "./models/llm")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH)
model.to(device)
generator = pipeline("text-generation", model=model, tokenizer=tokenizer, device=device)


def generate(prompt: str, max_new_tokens: int = 100, do_sample: bool = True, top_p: float = 0.95, temperature: float = 0.7) -> str:
    output = generator(prompt, max_new_tokens=max_new_tokens, do_sample=do_sample, top_p=top_p, temperature=temperature)
    return output[0]["generated_text"].replace(prompt, "").strip()

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
