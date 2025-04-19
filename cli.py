import os
import typer
from ai.generator import generate_commit_message, generate_pr_description
from utils.field_resolver import resolve_fields
from git.git_utils import get_staged_diff, commit_with_message
from jira.branch_helper import create_branch, find_branches

app = typer.Typer()

@app.command()
def ai_commit(ticket: str = typer.Option(None, help="Jira ticket ID to include as ref")):
    """
    Generate a commit message via AI and commit.
    """
    diff = get_staged_diff()
    message = generate_commit_message(diff, ticket)
    commit_with_message(message)
    typer.echo("Committed with AI-generated message.")

@app.command()
def ai_pr(ticket: str = typer.Argument(..., help="Jira ticket ID"), template: str = typer.Option("templates/pr_template.md")):
    """
    Generate a PR description for the given ticket.
    """
    # Load and resolve fields based on config
    fields = resolve_fields(ticket)
    description = generate_pr_description(fields, template)
    typer.echo(description)
    try:
        import pyperclip
        pyperclip.copy(description)
        typer.secho("PR description copied to clipboard.", fg=typer.colors.GREEN)
    except ImportError:
        typer.secho("pyperclip not installed, please install to enable --copy.", fg=typer.colors.YELLOW)

@app.command()
def branch(ticket: str = typer.Argument(..., help="Jira ticket ID"), mine: bool = typer.Option(False, help="Only tickets assigned to me")):
    """
    Create or find a branch for a given Jira ticket.
    """
    if mine:
        # logic to verify assignment can be added
        pass
    branch_name = create_branch(ticket)
    typer.echo(f"Using branch: {branch_name}")

@app.command()
def list_branches():
    """
    List existing branches related to your tickets.
    """
    branches = find_branches()
    for b in branches:
        typer.echo(b)

if __name__ == "__main__":
    app() 