import os
import logging
import re
from typing import List, Optional
from atlassian import Jira
from deep_translator import GoogleTranslator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")

jira_client = None

def _get_jira_client():
    global jira_client
    if jira_client is None:
        jira_client = _jira_client()
    return jira_client

class JiraError(Exception):
    """Exception raised for Jira API errors."""
    pass

def _jira_client() -> Jira:
    """
    Initialize and return a Jira client.
    
    Returns:
        Jira client instance
        
    Raises:
        JiraError: If required environment variables are missing or authentication fails
    """
    if not all([JIRA_URL, JIRA_USER, JIRA_TOKEN]):
        raise JiraError("Please set JIRA_URL, JIRA_USER, and JIRA_TOKEN environment variables.")
    
    try:
        client = Jira(url=JIRA_URL, username=JIRA_USER, password=JIRA_TOKEN)
        # Test the connection by making a simple request
        client.get_server_info()
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Jira client: {e}")
        raise JiraError(f"Failed to initialize Jira client: {str(e)}") from e

def sanitize_branch_name(name: str) -> str:
    """
    Sanitize a string to be used as a branch name.
    
    Args:
        name: The string to sanitize
        
    Returns:
        Sanitized string suitable for a branch name
    """
    # Replace spaces and special chars with hyphens
    sanitized = re.sub(r'[^a-zA-Z0-9-]', '-', name)
    # Remove consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    return sanitized.lower()

def create_branch(ticket: str, branch_type: str = "feature") -> str:
    """
    Create a new branch named {branch_type}/{ticket}-{short_desc} or return existing.
    
    Args:
        ticket: Jira ticket ID
        branch_type: Branch type prefix (feature, bugfix, hotfix, etc.)
        
    Returns:
        Branch name
        
    Raises:
        JiraError: If ticket retrieval fails
    """
    try:
        from git.git_utils import checkout_branch, current_branch
        
        # Validate inputs
        if not ticket or not re.match(r'^[A-Z]+-\d+$', ticket):
            logger.warning(f"Invalid ticket format: {ticket}. Expected format: ABC-123")
        
        # Check if branch already exists
        existing_branches = find_branches(ticket)
        if existing_branches:
            branch_name = existing_branches[0]
            logger.info(f"Branch for ticket {ticket} already exists: {branch_name}")
            checkout_branch(branch_name)
            return branch_name
        
        # Get ticket details from Jira
        try:
            jira = _get_jira_client()
            issue = jira.issue(ticket)
            
            # Get ticket summary
            summary = issue.get('fields', {}).get('summary', '')
            if not summary:
                logger.warning(f"Could not get summary for ticket {ticket}")
                summary = 'no-summary'
            
            # Translate non-ASCII summary to English
            if not summary.isascii():
                try:
                    translated = GoogleTranslator(source='auto', target='en').translate(summary)
                    if translated:
                        summary = translated
                    else:
                        logger.warning(f"Translation failed for: {summary}")
                except Exception as e:
                    logger.warning(f"Translation error: {e}")
            
            # Create sanitized branch name
            sanitized_summary = sanitize_branch_name(summary)
            branch_name = f"{branch_type}/{ticket}-{sanitized_summary[:50]}"
            
            # Create the branch
            success = checkout_branch(branch_name, create_new=True)
            if success:
                logger.info(f"Created and checked out branch: {branch_name}")
                return branch_name
            else:
                raise JiraError(f"Failed to create branch: {branch_name}")
                
        except Exception as e:
            logger.error(f"Error getting Jira ticket {ticket}: {e}")
            # Fallback to simple branch name if Jira fails
            branch_name = f"{branch_type}/{ticket}"
            success = checkout_branch(branch_name, create_new=True)
            if success:
                return branch_name
            raise JiraError(f"Failed to create branch for ticket {ticket}: {str(e)}")
            
    except Exception as e:
        logger.error(f"Branch creation failed: {e}")
        raise

def find_branches(ticket: str = None) -> List[str]:
    """
    List all local branches, optionally filtered by ticket.
    
    Args:
        ticket: Optional Jira ticket ID to filter branches
        
    Returns:
        List of matching branch names
    """
    try:
        from git.git_utils import list_local_branches
        branches = list_local_branches()
        
        if ticket:
            # Ensure case-insensitive matching
            branches = [branch for branch in branches if ticket.lower() in branch.lower()]
            
        return branches
    except Exception as e:
        logger.error(f"Error listing branches: {e}")
        return []
