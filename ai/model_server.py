from fastapi import FastAPI, Request
import uvicorn
from pydantic import BaseModel
from typing import Dict, Optional, Any
import logging
import os
from contextlib import asynccontextmanager

# Import the model functionality
from ai.client import prepare_model, generate, generate_commit_message, generate_pr_description

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load model when the server starts
    logger.info("Loading model...")
    prepare_model()
    logger.info("Model loaded successfully")
    
    yield
    
    # Shutdown: Any cleanup could go here if needed

app = FastAPI(title="BitJira-Lifter Model Server", lifespan=lifespan)

class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 100
    do_sample: bool = True
    top_p: float = 0.95
    temperature: float = 0.7

class CommitRequest(BaseModel):
    diff: str
    ticket: Optional[str] = None

class PRRequest(BaseModel):
    ticket: str
    diff: str
    template: Optional[str] = None

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.post("/generate")
def generate_text(req: GenerateRequest):
    """Generate text based on prompt"""
    try:
        result = generate(
            prompt=req.prompt,
            max_new_tokens=req.max_new_tokens,
            do_sample=req.do_sample,
            top_p=req.top_p,
            temperature=req.temperature
        )
        return {"text": result}
    except Exception as e:
        logger.error(f"Error in generation: {e}")
        return {"error": str(e), "text": ""}

@app.post("/commit")
def commit_message(req: CommitRequest):
    """Generate commit message from diff and optional ticket"""
    try:
        message = generate_commit_message(diff=req.diff, ticket=req.ticket)
        return {"message": message}
    except Exception as e:
        logger.error(f"Error generating commit message: {e}")
        return {"error": str(e), "message": ""}

@app.post("/pr")
def pr_description(req: PRRequest):
    """Generate PR description from ticket, diff and optional template"""
    try:
        description = generate_pr_description(
            ticket=req.ticket,
            diff=req.diff,
            template_path=req.template
        )
        return {"description": description}
    except Exception as e:
        logger.error(f"Error generating PR description: {e}")
        return {"error": str(e), "description": ""}

def start_server(host="127.0.0.1", port=8000):
    """Start the model server"""
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    # Get host and port from environment or use defaults
    host = os.getenv("MODEL_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MODEL_SERVER_PORT", "8000"))
    
    start_server(host, port) 