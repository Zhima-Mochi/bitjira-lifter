import os
import logging
from typing import Generator, List, Dict, Optional, Any
from atlassian.bitbucket import Cloud
from atlassian.bitbucket.cloud.workspaces import Workspace
from atlassian.bitbucket.cloud.workspaces import Projects
from atlassian.bitbucket.cloud.repositories import Repository

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
BITBUCKET_USER = os.getenv("BITBUCKET_USER")
BITBUCKET_APP_PASSWORD = os.getenv("BITBUCKET_APP_PASSWORD")
BITBUCKET_WORKSPACE = os.getenv("BITBUCKET_WORKSPACE")

bitbucket_client = None

def _get_bitbucket_client():
    global bitbucket_client
    if bitbucket_client is None:
        bitbucket_client = _bitbucket_client()
    return bitbucket_client

class BitbucketError(Exception):
    """Exception raised for Bitbucket API errors."""
    pass

def _bitbucket_client() -> Cloud:
    """
    Initialize and return a Bitbucket Cloud client.
    
    Returns:
        Bitbucket Cloud client instance
        
    Raises:
        BitbucketError: If required environment variables are missing or authentication fails
    """
    if not BITBUCKET_USER or not BITBUCKET_APP_PASSWORD:
        logger.error("Bitbucket credentials not set in environment variables")
        raise BitbucketError(
            "Please set BITBUCKET_USER and BITBUCKET_APP_PASSWORD environment variables.")

    try:
        client = Cloud(
            username=BITBUCKET_USER,
            password=BITBUCKET_APP_PASSWORD,
            cloud=True
        )
        # Test connection by making a simple request
        client.workspaces.get_avatar(BITBUCKET_WORKSPACE)
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Bitbucket client: {e}")
        raise BitbucketError(f"Failed to initialize Bitbucket client: {str(e)}") from e

def list_workspaces() -> List[Dict[str, Any]]:
    """
    List all workspaces accessible to the authenticated user.
    
    Returns:
        List of workspace dictionaries
        
    Raises:
        BitbucketError: If the API request fails
    """
    try:
        bb = _get_bitbucket_client()
        workspaces = list(bb.workspaces.each())
        logger.info(f"Found {len(workspaces)} Bitbucket workspaces")
        return workspaces
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}")
        raise BitbucketError(f"Error listing workspaces: {str(e)}") from e

def get_workspace(workspace_slug: str = BITBUCKET_WORKSPACE) -> Workspace:
    """
    Get a specific workspace by slug.
    
    Args:
        workspace_slug: The workspace slug to retrieve
        
    Returns:
        Workspace object
        
    Raises:
        BitbucketError: If the workspace cannot be found or accessed
    """
    if not workspace_slug:
        logger.error("No workspace slug provided and BITBUCKET_WORKSPACE not set")
        raise BitbucketError("No workspace slug provided")
        
    try:
        bb = _get_bitbucket_client()
        workspace = bb.workspaces.get(workspace_slug)
        logger.info(f"Retrieved workspace: {workspace_slug}")
        return workspace
    except Exception as e:
        logger.error(f"Error getting workspace {workspace_slug}: {e}")
        raise BitbucketError(f"Error getting workspace {workspace_slug}: {str(e)}") from e

def list_projects(workspace_slug: str = BITBUCKET_WORKSPACE) -> List[Dict[str, Any]]:
    """
    List all projects in a workspace.
    
    Args:
        workspace_slug: The workspace slug containing the projects
        
    Returns:
        List of project dictionaries
        
    Raises:
        BitbucketError: If the API request fails
    """
    if not workspace_slug:
        logger.error("No workspace slug provided and BITBUCKET_WORKSPACE not set")
        raise BitbucketError("No workspace slug provided")
        
    try:
        bb = _get_bitbucket_client()
        projects = list(bb.workspaces.get(workspace_slug).projects.each())
        logger.info(f"Found {len(projects)} projects in workspace {workspace_slug}")
        return projects
    except Exception as e:
        logger.error(f"Error listing projects in workspace {workspace_slug}: {e}")
        raise BitbucketError(f"Error listing projects in workspace {workspace_slug}: {str(e)}") from e

def list_repos(workspace_slug: str = BITBUCKET_WORKSPACE) -> List[Dict[str, Any]]:
    """
    List all repositories in a workspace.
    
    Args:
        workspace_slug: The workspace slug containing the repositories
        
    Returns:
        List of repository dictionaries
        
    Raises:
        BitbucketError: If the API request fails
    """
    if not workspace_slug:
        logger.error("No workspace slug provided and BITBUCKET_WORKSPACE not set")
        raise BitbucketError("No workspace slug provided")
        
    try:
        bb = _get_bitbucket_client()
        repos = list(bb.workspaces.get(workspace_slug).repositories.each())
        logger.info(f"Found {len(repos)} repositories in workspace {workspace_slug}")
        return repos
    except Exception as e:
        logger.error(f"Error listing repositories in workspace {workspace_slug}: {e}")
        raise BitbucketError(f"Error listing repositories in workspace {workspace_slug}: {str(e)}") from e

def get_repo(repo_slug: str, workspace_slug: str = BITBUCKET_WORKSPACE) -> Repository:
    """
    Get a specific repository by slug.
    
    Args:
        repo_slug: The repository slug to retrieve
        workspace_slug: The workspace slug containing the repository
        
    Returns:
        Repository object
        
    Raises:
        BitbucketError: If the repository cannot be found or accessed
    """
    if not workspace_slug:
        logger.error("No workspace slug provided and BITBUCKET_WORKSPACE not set")
        raise BitbucketError("No workspace slug provided")
        
    if not repo_slug:
        logger.error("No repository slug provided")
        raise BitbucketError("No repository slug provided")
        
    try:
        bb = _get_bitbucket_client()
        repo = bb.workspaces.get(workspace_slug).repositories.get(repo_slug)
        logger.info(f"Retrieved repository: {repo_slug} in workspace {workspace_slug}")
        return repo
    except Exception as e:
        logger.error(f"Error getting repository {repo_slug} in workspace {workspace_slug}: {e}")
        raise BitbucketError(f"Error getting repository {repo_slug} in workspace {workspace_slug}: {str(e)}") from e
        
def create_pull_request(
    repo_slug: str, 
    source_branch: str, 
    destination_branch: str = "main", 
    title: str = None, 
    description: str = None, 
    workspace_slug: str = BITBUCKET_WORKSPACE
) -> Dict[str, Any]:
    """
    Create a pull request in a repository.
    
    Args:
        repo_slug: The repository slug where the PR will be created
        source_branch: The source branch for the PR
        destination_branch: The destination branch for the PR (default: main)
        title: The PR title (default: derived from source branch)
        description: The PR description (default: empty)
        workspace_slug: The workspace slug containing the repository
        
    Returns:
        Dictionary with PR details
        
    Raises:
        BitbucketError: If the PR cannot be created
    """
    if not title:
        # Generate title from branch name if not provided
        title = f"Merge {source_branch} into {destination_branch}"
        
    try:
        bb = _get_bitbucket_client()
        repo = bb.workspaces.get(workspace_slug).repositories.get(repo_slug)
        
        # Create PR
        pr_data = {
            "title": title,
            "description": description or "",
            "source": {"branch": {"name": source_branch}},
            "destination": {"branch": {"name": destination_branch}}
        }
        
        pr = repo.pullrequests.create(pr_data)
        logger.info(f"Created PR: {title} in {repo_slug}")
        return pr
    except Exception as e:
        logger.error(f"Error creating PR in repository {repo_slug}: {e}")
        raise BitbucketError(f"Error creating PR in repository {repo_slug}: {str(e)}") from e
