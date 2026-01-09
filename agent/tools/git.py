import subprocess
from typing import Optional, Tuple


def run_git(*args: str, cwd: str = ".") -> Tuple[bool, str]:
    """Run a git command and return (success, output)."""
    try:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=cwd,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def create_branch(branch_name: str, base: str = "main") -> Tuple[bool, str]:
    """Create and checkout a new branch, or checkout if it exists."""
    run_git("fetch", "origin")
    
    # Try to create new branch
    success, output = run_git("checkout", "-b", branch_name, f"origin/{base}")
    if success:
        return True, f"Created and checked out {branch_name}"
    
    # Branch might exist - try checking it out
    success, output = run_git("checkout", branch_name)
    if success:
        # Pull latest changes
        run_git("pull", "origin", branch_name)
        return True, f"Checked out existing branch {branch_name}"
    
    return False, f"Failed to create/checkout branch: {output}"


def checkout_branch(branch_name: str) -> bool:
    """Checkout an existing branch."""
    success, _ = run_git("checkout", branch_name)
    return success


def commit_changes(message: str, files: list[str] = None) -> bool:
    """Stage and commit changes."""
    if files:
        for file in files:
            run_git("add", file)
    else:
        run_git("add", "-A")

    success, _ = run_git("commit", "-m", message)
    return success


def push_branch(branch_name: str) -> bool:
    """Push branch to origin."""
    success, _ = run_git("push", "-u", "origin", branch_name)
    return success


def create_pr(title: str, body: str, base: str = "main") -> Tuple[bool, Optional[str]]:
    """Create a PR using GitHub CLI and return (success, pr_url)."""
    try:
        result = subprocess.run(
            ["gh", "pr", "create", "--title", title, "--body", body, "--base", base],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # gh pr create outputs the PR URL
            return True, result.stdout.strip()
        return False, result.stderr
    except Exception as e:
        return False, str(e)


def get_current_branch() -> str:
    """Get the current branch name."""
    success, output = run_git("branch", "--show-current")
    return output.strip() if success else ""
