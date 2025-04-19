import subprocess
from typing import List


def run_cmd(cmd: list) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def get_staged_diff() -> str:
    return run_cmd(["git", "diff", "--staged"])


def commit_with_message(message: str):
    subprocess.run(["git", "commit", "-m", message])


def list_local_branches() -> List[str]:
    out = run_cmd(["git", "branch"])
    return [line.strip().lstrip("* ") for line in out.splitlines()]


def checkout_branch(name: str, create_new: bool = False):
    cmd = ["git", "checkout"]
    if create_new:
        cmd += ["-b", name]
    else:
        cmd.append(name)
    run_cmd(cmd) 