import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.WARNING)

import os
import typer
from typing import Optional
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    logger.info("Environment variables loaded")
except ImportError:
    logger.warning("dotenv not installed, using existing environment variables")


from ai.generator import generate_commit_message, generate_pr_description
from git.git_utils import get_staged_diff, commit_with_message, GitError, current_branch, get_diff_to_target_branch
from jira.branch_helper import create_branch, find_branches, JiraError
from bitbucket.cloud_helper import create_pull_request, BitbucketError

app = typer.Typer(help="BitJira Lifter: CLI tool for AI-driven Git and Jira workflow")

@app.command()
def prepare_model():
    from ai.generator import prepare_model
    prepare_model()

@app.command()
def generate(
    prompt: str = typer.Argument(..., help="Prompt to generate text from"),
    max_new_tokens: int = typer.Option(100, help="Maximum number of tokens to generate"),
    do_sample: bool = typer.Option(True, help="Sample from the model"),
    top_p: float = typer.Option(0.95, help="Top-p sampling parameter"),
    temperature: float = typer.Option(0.7, help="Temperature for the model"),
):
    from ai.generator import generate
    print(generate(prompt, max_new_tokens, do_sample, top_p, temperature))

@app.command()
def ai_commit(
    ticket: Optional[str] = typer.Option(None, help="Jira ticket ID to include as ref"),
    force: bool = typer.Option(False, "--force", "-f", help="Commit even if there are errors")
):
    """
    Generate a commit message via AI and commit.
    """
    try:
        diff = get_staged_diff()
        if not diff:
            typer.secho("No staged changes to commit.", fg=typer.colors.YELLOW)
            return
            
        typer.echo("Generating commit message...")
        message = generate_commit_message(diff, ticket)
        
        if not message:
            typer.secho("Failed to generate commit message.", fg=typer.colors.RED)
            return
            
        # Show preview
        typer.echo("\nCommit message:")
        typer.secho(message, fg=typer.colors.GREEN)
        
        # Confirm
        if not force and not typer.confirm("Proceed with commit?"):
            typer.echo("Commit cancelled.")
            return
            
        # Commit
        success = commit_with_message(message)
        if success:
            typer.secho("Changes committed successfully.", fg=typer.colors.GREEN)
        else:
            typer.secho("Commit failed. See log for details.", fg=typer.colors.RED)
            
    except GitError as e:
        typer.secho(f"Git error: {str(e)}", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"Unexpected error: {str(e)}", fg=typer.colors.RED)
        if force:
            typer.echo("Trying to commit anyway...")
            commit_with_message(message)

@app.command()
def ai_pr(
    ticket: str = typer.Argument(..., help="Jira ticket ID"),
    template: str = typer.Option("templates/pr_template", help="Path to PR template"),
    copy: bool = typer.Option(True, help="Copy to clipboard")
):
    """
    Generate a PR description for the given ticket.
    """
    try:
        # Ensure template exists
        if not Path(template).exists():
            template_fallback = os.path.join("templates", "pr_template.example")
            if Path(template_fallback).exists():
                typer.secho(f"Template {template} not found, using example template.", fg=typer.colors.YELLOW)
                template = template_fallback
            else:
                typer.secho(f"Template {template} not found and no fallback available.", fg=typer.colors.RED)
                return
        
        # Get the diff for context
        typer.echo(f"Fetching diff data for ticket {ticket}...")
        diff = get_diff_to_target_branch()
        
        # Generate description
        typer.echo("Generating PR description...")
        description = generate_pr_description(ticket, diff, template)
        
        # Output
        typer.echo("\nPR Description:")
        typer.echo(description)
        
        # Copy to clipboard if requested
        if copy:
            try:
                import pyperclip
                pyperclip.copy(description)
                typer.secho("PR description copied to clipboard.", fg=typer.colors.GREEN)
            except ImportError:
                typer.secho("pyperclip not installed, please install to enable --copy.", fg=typer.colors.YELLOW)
            except Exception as e:
                typer.secho(f"Failed to copy to clipboard: {str(e)}", fg=typer.colors.YELLOW)
                
    except Exception as e:
        typer.secho(f"Error generating PR description: {str(e)}", fg=typer.colors.RED)

@app.command()
def branch(
    ticket: str = typer.Argument(..., help="Jira ticket ID"), 
    branch_type: str = typer.Option("feature", help="Branch type (feature, bugfix, etc.)"),
    mine: bool = typer.Option(False, help="Only tickets assigned to me")
):
    """
    Create or find a branch for a given Jira ticket.
    """
    try:
        if mine:
            # logic to verify assignment can be added later
            typer.echo("Checking for ticket assignment...")
            
        typer.echo(f"Creating branch for ticket {ticket}...")
        branch_name = create_branch(ticket, branch_type)
        typer.secho(f"Using branch: {branch_name}", fg=typer.colors.GREEN)
        
    except JiraError as e:
        typer.secho(f"Jira error: {str(e)}", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"Unexpected error: {str(e)}", fg=typer.colors.RED)

@app.command()
def list_branches(
    ticket: Optional[str] = typer.Option(None, help="Filter by ticket ID")
):
    """
    List existing branches related to your tickets.
    """
    try:
        branches = find_branches(ticket)
        
        if not branches:
            if ticket:
                typer.echo(f"No branches found for ticket {ticket}.")
            else:
                typer.echo("No branches found.")
            return
            
        typer.echo(f"Found {len(branches)} branches:")
        for i, b in enumerate(branches, 1):
            typer.secho(f"{i}. {b}", fg=typer.colors.GREEN)
            
    except Exception as e:
        typer.secho(f"Error listing branches: {str(e)}", fg=typer.colors.RED)

@app.command()
def create_pr(
    ticket: Optional[str] = typer.Option(None, help="Jira ticket ID (extracts from branch name if not provided)"),
    repo: str = typer.Option(None, help="Repository slug (required)"),
    source: Optional[str] = typer.Option(None, help="Source branch (uses current branch if not provided)"),
    destination: str = typer.Option("main", help="Destination branch"),
    create_desc: bool = typer.Option(True, help="Generate PR description automatically")
):
    """
    Create a pull request on Bitbucket.
    """
    try:
        # Get current branch if source not provided
        if not source:
            source = current_branch()
            if not source:
                typer.secho("Could not determine current branch.", fg=typer.colors.RED)
                return
            typer.echo(f"Using current branch: {source}")
            
        # Extract ticket ID from branch if not provided
        if not ticket:
            import re
            match = re.search(r'[A-Z]+-\d+', source)
            if match:
                ticket = match.group(0)
                typer.echo(f"Extracted ticket ID from branch: {ticket}")
            else:
                typer.secho("Could not extract ticket ID from branch name. Please provide it explicitly.", fg=typer.colors.YELLOW)
                
        # Require repository slug
        if not repo:
            typer.secho("Repository slug is required. Use --repo option.", fg=typer.colors.RED)
            return
            
        # Generate description if requested
        description = None
        if create_desc and ticket:
            try:
                typer.echo(f"Generating description for ticket {ticket}...")
                diff = get_diff_to_target_branch()
                template_path = "templates/pr_template"
                if not Path(template_path).exists():
                    template_path = "templates/pr_template.example"
                description = generate_pr_description(ticket, diff, template_path)
            except Exception as e:
                typer.secho(f"Error generating PR description: {e}", fg=typer.colors.YELLOW)
                
        # Create PR title
        title = f"[{ticket}] " if ticket else ""
        title += f"Merge {source} into {destination}"
        
        # Confirm
        typer.echo("\nAbout to create PR with:")
        typer.echo(f"Repository: {repo}")
        typer.echo(f"Source branch: {source}")
        typer.echo(f"Destination branch: {destination}")
        typer.echo(f"Title: {title}")
        
        if not typer.confirm("Proceed?"):
            typer.echo("Operation cancelled.")
            return
            
        # Create PR
        typer.echo("Creating pull request...")
        pr = create_pull_request(
            repo_slug=repo,
            source_branch=source,
            destination_branch=destination,
            title=title,
            description=description
        )
        
        typer.secho(f"Pull request created successfully!", fg=typer.colors.GREEN)
        if pr.get('links', {}).get('html', {}).get('href'):
            typer.echo(f"PR URL: {pr['links']['html']['href']}")
            
    except (GitError, BitbucketError, JiraError) as e:
        typer.secho(f"Error: {str(e)}", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"Unexpected error: {str(e)}", fg=typer.colors.RED)

if __name__ == "__main__":
    app()