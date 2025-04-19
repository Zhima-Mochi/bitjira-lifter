import subprocess
import logging
from typing import List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GitError(Exception):
    """Exception raised for Git command errors."""
    pass

def run_cmd(cmd: list) -> str:
    """
    Run a git command and return stdout and stderr.
    
    Args:
        cmd: List of command components
        check: Whether to raise an exception on non-zero exit code
        
    Returns:
        Tuple of (stdout, stderr)
        
    Raises:
        GitError: If the command fails and check is True
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GitError(f"Error executing git command: {str(e)}") from e

def get_staged_diff() -> str:
    """Get the diff of staged changes."""
    return run_cmd(["git", "diff", "--staged"])

def is_repo_clean() -> bool:
    """Check if the repository has any uncommitted changes."""
    return run_cmd(["git", "status", "--porcelain"]) == ""

def commit_with_message(message: str) -> bool:
    """
    Commit with the given message.
    
    Returns:
        True if the commit was successful, False otherwise
    """
    try:
        run_cmd(["git", "commit", "-m", message])
        return True
    except GitError:
        return False

def list_local_branches() -> List[str]:
    """List all local branches."""
    return [line.strip().lstrip("* ") for line in run_cmd(["git", "branch"]).splitlines()]

def checkout_branch(name: str, create_new: bool = False) -> bool:
    """
    Checkout a branch, optionally creating it.
    
    Args:
        name: Branch name
        create_new: Whether to create a new branch
        
    Returns:
        True if checkout was successful, False otherwise
    """
    cmd = ["git", "checkout"]
    if create_new:
        cmd += ["-b", name]
    else:
        cmd.append(name)
    
    try:
        run_cmd(cmd)
        return True
    except GitError:
        return False

def current_branch() -> Optional[str]:
    """Get the name of the current branch."""
    try:
        return run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    except GitError:
        return None

def pull_latest() -> bool:
    """Pull the latest changes from the remote."""
    try:
        run_cmd(["git", "pull"])
        return True
    except GitError:
        return False 