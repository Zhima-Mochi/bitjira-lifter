import subprocess
import logging
from typing import List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GitError(Exception):
    """Exception raised for Git command errors."""
    pass

def run_cmd(cmd: list) -> str:
    """
    Run a git command and return stdout.
    
    Args:
        cmd: List of command components
        
    Returns:
        Command output as string
        
    Raises:
        GitError: If the command fails with non-zero exit code
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_msg = f"Error executing command '{' '.join(cmd)}': {e.stderr.strip()}"
        logger.error(error_msg)
        raise GitError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error executing command '{' '.join(cmd)}': {str(e)}"
        logger.error(error_msg)
        raise GitError(error_msg) from e

def get_staged_diff() -> str:
    """
    Get the diff of staged changes.
    
    Returns:
        Git diff output as string
        
    Raises:
        GitError: If git diff command fails
    """
    return run_cmd(["git", "diff", "--staged"])

def get_diff_to_target_branch(target_branch: str = "dev") -> str:
    """
    Get the diff of changes compared to the target branch.
    
    Args:
        target_branch: Target branch to compare against, defaults to "dev"
        
    Returns:
        Git diff output as string
        
    Raises:
        GitError: If git diff command fails
    """
    return run_cmd(["git", "diff", target_branch])

def is_repo_clean() -> bool:
    """
    Check if the repository has any uncommitted changes.
    
    Returns:
        True if the repository is clean, False otherwise
    """
    try:
        return run_cmd(["git", "status", "--porcelain"]) == ""
    except GitError:
        logger.warning("Failed to check if repo is clean, assuming it's not")
        return False

def commit_with_message(message: str) -> bool:
    """
    Commit with the given message.
    
    Args:
        message: Commit message
    
    Returns:
        True if the commit was successful, False otherwise
    """
    try:
        run_cmd(["git", "commit", "-m", message])
        return True
    except GitError:
        logger.error("Failed to commit changes")
        return False

def list_local_branches() -> List[str]:
    """
    List all local branches.
    
    Returns:
        List of branch names
        
    Raises:
        GitError: If git branch command fails
    """
    try:
        output = run_cmd(["git", "branch"])
        return [line.strip().lstrip("* ") for line in output.splitlines()]
    except GitError:
        logger.error("Failed to list local branches")
        return []

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
        logger.error(f"Failed to checkout branch '{name}'")
        return False

def current_branch() -> Optional[str]:
    """
    Get the name of the current branch.
    
    Returns:
        Current branch name or None if error
    """
    try:
        return run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    except GitError:
        logger.error("Failed to get current branch name")
        return None

def pull_latest() -> bool:
    """
    Pull the latest changes from the remote.
    
    Returns:
        True if pull was successful, False otherwise
    """
    try:
        run_cmd(["git", "pull"])
        return True
    except GitError:
        logger.error("Failed to pull latest changes")
        return False 