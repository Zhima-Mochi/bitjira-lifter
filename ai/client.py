import os
import requests
import logging
from typing import Dict, Optional, Any
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from accelerate import Accelerator

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default server URL
DEFAULT_SERVER_URL = "http://127.0.0.1:8000"

# Initialize accelerator
accelerator = Accelerator()
DEVICE = accelerator.device

# Model state (for direct generation)
MODEL_LOADED = False
MODEL = None
TOKENIZER = None
GENERATOR = None

# Create singleton client
_client = None

def get_client() -> 'ModelClient':
    """Get or create the model client singleton"""
    global _client
    if _client is None:
        _client = ModelClient()
    return _client

# Client for model server
class ModelClient:
    """Client to interact with the model server"""
    
    def __init__(self, server_url: str = None):
        """Initialize client with server URL"""
        self.server_url = server_url or os.getenv("MODEL_SERVER_URL", DEFAULT_SERVER_URL)
        self.session = requests.Session()
        self._server_available = None  # Cache for server availability status
        
    def check_health(self) -> bool:
        """Check if the model server is running"""
        try:
            response = self.session.get(f"{self.server_url}/health", timeout=2)
            self._server_available = response.status_code == 200
            return self._server_available
        except requests.RequestException as e:
            logger.warning(f"Model server health check failed: {e}")
            self._server_available = False
            return False
    
    def is_server_available(self) -> bool:
        """Check if server is available (using cached value if possible)"""
        if self._server_available is None:
            return self.check_health()
        return self._server_available
    
    def generate(self, prompt: str, max_new_tokens: int = 1000, 
                 do_sample: bool = True, top_p: float = 0.95, 
                 temperature: float = 0.7) -> str:
        """Generate text from prompt using the model server or fallback to direct generation"""
        if not self.is_server_available():
            logger.info("Server unavailable, using direct model generation")
            return _generate_with_model(prompt, max_new_tokens, do_sample, top_p, temperature)
            
        try:
            response = self.session.post(
                f"{self.server_url}/generate",
                json={
                    "prompt": prompt,
                    "max_new_tokens": max_new_tokens,
                    "do_sample": do_sample,
                    "top_p": top_p,
                    "temperature": temperature
                },
                timeout=30  # Longer timeout for generation
            )
            response.raise_for_status()
            result = response.json()
            return result.get("text", "")
        except requests.RequestException as e:
            logger.warning(f"Model server request failed, falling back to direct generation: {e}")
            self._server_available = False  # Mark server as unavailable
            return _generate_with_model(prompt, max_new_tokens, do_sample, top_p, temperature)
    
    def generate_commit_message(self, diff: str, ticket: Optional[str] = None) -> str:
        """Generate commit message from diff and optional ticket"""
        if not self.is_server_available():
            logger.info("Server unavailable, using direct model generation for commit message")
            return _generate_commit_message_with_model(diff, ticket)
            
        try:
            response = self.session.post(
                f"{self.server_url}/commit",
                json={"diff": diff, "ticket": ticket},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result.get("message", "")
        except requests.RequestException as e:
            logger.warning(f"Model server request failed, falling back to direct generation: {e}")
            self._server_available = False
            return _generate_commit_message_with_model(diff, ticket)
    
    def generate_pr_description(self, ticket: str, diff: str, 
                                template: Optional[str] = None) -> str:
        """Generate PR description from ticket, diff and optional template"""
        if not self.is_server_available():
            logger.info("Server unavailable, using direct model generation for PR description")
            return _generate_pr_description_with_model(ticket, diff, template)
            
        try:
            response = self.session.post(
                f"{self.server_url}/pr",
                json={"ticket": ticket, "diff": diff, "template": template},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result.get("description", "")
        except requests.RequestException as e:
            logger.warning(f"Model server request failed, falling back to direct generation: {e}")
            self._server_available = False
            return _generate_pr_description_with_model(ticket, diff, template)

# Internal model functions (private)
def prepare_model(model_id: str = None):
    """
    Load model from local path or HuggingFace.
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

def _prepare_generator():
    global GENERATOR
    if GENERATOR:
        return
    prepare_model()
    if not MODEL_LOADED:
        return
    GENERATOR = pipeline("text-generation", model=MODEL, tokenizer=TOKENIZER, device=DEVICE)

def _generate_with_model(prompt: str, max_new_tokens: int = 1000, 
                         do_sample: bool = True, top_p: float = 0.95, 
                         temperature: float = 0.7) -> str:
    """Generate text using the loaded model (internal function)"""
    _prepare_generator()
    if not MODEL_LOADED:
        return f"[AI generation unavailable - placeholder for: {prompt[:30]}...]"

    try:
        output = GENERATOR(prompt, max_new_tokens=max_new_tokens,
                           do_sample=do_sample, top_p=top_p, temperature=temperature)
        return output[0]["generated_text"].replace(prompt, "").strip()
    except Exception as e:
        logger.error(f"Error during text generation: {e}")
        return f"[Error during generation: {str(e)[:50]}...]"

def _generate_commit_message_with_model(diff: str, ticket: Optional[str] = None) -> str:
    """Generate commit message directly with model (internal function)"""
    prompt = f"Generate a clear and concise commit message for the following code changes:\n\n{diff[:5000]}"
    if ticket:
        prompt += f"\n\nInclude the reference to Jira ticket {ticket} in the message."

    message = _generate_with_model(prompt, max_new_tokens=150)
    return message

def _generate_pr_description_with_model(ticket: str, diff: str, template_path: Optional[str] = None) -> str:
    """Generate PR description directly with model (internal function)"""
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
        description = _generate_with_model(description_prompt, max_new_tokens=150)
        return description
    except Exception as e:
        logger.error(f"Error generating PR description: {e}")
        return f"Failed to generate PR description: {str(e)}"

# Public API functions - these are the ones used by cli.py
def generate(prompt: str, max_new_tokens: int = 1000, 
             do_sample: bool = True, top_p: float = 0.95, 
             temperature: float = 0.7) -> str:
    """Generate text using the model server or direct model generation"""
    return get_client().generate(
        prompt=prompt,
        max_new_tokens=max_new_tokens,
        do_sample=do_sample,
        top_p=top_p,
        temperature=temperature
    )

def generate_commit_message(diff: str, ticket: Optional[str] = None) -> str:
    """Generate commit message using the model server or direct model generation"""
    return get_client().generate_commit_message(diff=diff, ticket=ticket)

def generate_pr_description(ticket: str, diff: str, template_path: Optional[str] = None) -> str:
    """Generate PR description using the model server or direct model generation"""
    return get_client().generate_pr_description(ticket=ticket, diff=diff, template=template_path)
