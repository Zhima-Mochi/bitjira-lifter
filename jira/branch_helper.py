import os
from atlassian import Jira

JIRA_URL = os.getenv("JIRA_URL")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")

def _jira_client():
    if not all([JIRA_URL, JIRA_USER, JIRA_TOKEN]):
        raise ValueError("Please set JIRA_URL, JIRA_USER, and JIRA_TOKEN environment variables.")
    return Jira(url=JIRA_URL, username=JIRA_USER, password=JIRA_TOKEN)


def create_branch(ticket: str) -> str:
    """
    Create a new branch named feature/{ticket}-{short_desc} or return existing.
    """
    from git.git_utils import get_current_branch, checkout_branch
    jira = _jira_client()
    issue = jira.issue(ticket)
    summary = issue.fields.summary.replace(" ", "-").lower()
    branch_name = f"feature/{ticket}-{summary[:50]}"

    existing = find_branches()
    if branch_name in existing:
        checkout_branch(branch_name)
    else:
        checkout_branch(branch_name, create_new=True)
    return branch_name


def find_branches() -> list:
    """List all local branches."""
    from git.git_utils import list_local_branches
    return list_local_branches() 