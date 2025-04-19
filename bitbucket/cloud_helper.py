from typing import Generator
from atlassian.bitbucket import Cloud
from atlassian.bitbucket.cloud.workspaces import Workspace
from atlassian.bitbucket.cloud.workspaces import Projects
from atlassian.bitbucket.cloud.repositories import Repository
import os

BITBUCKET_USER = os.getenv("BITBUCKET_USER")
BITBUCKET_APP_PASSWORD = os.getenv("BITBUCKET_APP_PASSWORD")
BITBUCKET_WORKSPACE = os.getenv("BITBUCKET_WORKSPACE")


def _bitbucket_client() -> Cloud:
    if not BITBUCKET_USER or not BITBUCKET_APP_PASSWORD:
        raise EnvironmentError(
            "Please set BITBUCKET_USER and BITBUCKET_APP_PASSWORD environment variables.")

    return Cloud(
        username=BITBUCKET_USER,
        password=BITBUCKET_APP_PASSWORD,
        cloud=True
    )


def list_workspaces() -> Generator[Workspace, None, None]:
    bb = _bitbucket_client()
    return bb.workspaces.each()


def get_workspace(workspace_slug: str = BITBUCKET_WORKSPACE) -> Workspace:
    bb = _bitbucket_client()
    return bb.workspaces.get(workspace_slug)


def list_projects(workspace_slug: str = BITBUCKET_WORKSPACE) -> Generator[Projects, None, None]:
    bb = _bitbucket_client()
    return bb.workspaces.get(workspace_slug).projects.each()


def list_repos(workspace_slug: str = BITBUCKET_WORKSPACE) -> Generator[Repository, None, None]:
    bb = _bitbucket_client()
    return bb.workspaces.get(workspace_slug).repositories.each()


def get_repo(repo_slug: str, workspace_slug: str = BITBUCKET_WORKSPACE) -> Repository:
    bb = _bitbucket_client()
    return bb.workspaces.get(workspace_slug).repositories.get(repo_slug)
