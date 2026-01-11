"""GitHub Adapter - Interact with GitHub API for PR status checks."""
import os
import re
import httpx
from typing import Optional, List
from pydantic import BaseModel

GITHUB_API_URL = "https://api.github.com"


class PullRequest(BaseModel):
    """Representation of a GitHub PR."""
    number: int
    title: str
    state: str  # open, closed
    merged: bool
    html_url: str
    head_ref: str  # branch name


class GitHubAdapter:
    """Adapter for GitHub API interactions."""

    def __init__(self):
        self.api_key = os.getenv("GITHUB_API_KEY")
        if not self.api_key:
            raise ValueError("GITHUB_API_KEY not set")
        
        # Get repo from env - optional, can extract from PR URLs
        self.repo = os.getenv("GITHUB_REPO", "")  # format: owner/repo
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def _get(self, path: str) -> dict:
        """Execute a GET request to GitHub API."""
        url = f"{GITHUB_API_URL}{path}"
        response = httpx.get(url, headers=self.headers)
        if response.status_code != 200:
            print(f"GitHub API error: {response.status_code} - {response.text}")
        response.raise_for_status()
        return response.json()

    def get_pr_by_url(self, pr_url: str) -> Optional[PullRequest]:
        """Get PR details from a GitHub PR URL.
        
        Args:
            pr_url: Full PR URL like https://github.com/owner/repo/pull/123
            
        Returns:
            PullRequest object or None if not found
        """
        # Extract PR number from URL
        match = re.search(r'/pull/(\d+)', pr_url)
        if not match:
            print(f"Could not extract PR number from: {pr_url}")
            return None
        
        pr_number = int(match.group(1))
        
        # Extract owner/repo from URL or use configured repo
        repo_match = re.search(r'github\.com/([^/]+/[^/]+)/pull', pr_url)
        repo = repo_match.group(1) if repo_match else self.repo
        
        try:
            data = self._get(f"/repos/{repo}/pulls/{pr_number}")
            return PullRequest(
                number=data["number"],
                title=data["title"],
                state=data["state"],
                merged=data.get("merged", False),
                html_url=data["html_url"],
                head_ref=data["head"]["ref"]
            )
        except Exception as e:
            print(f"Error fetching PR {pr_number}: {e}")
            return None

    def is_pr_merged(self, pr_url: str) -> bool:
        """Check if a PR has been merged.
        
        Args:
            pr_url: Full PR URL
            
        Returns:
            True if merged, False otherwise
        """
        pr = self.get_pr_by_url(pr_url)
        if not pr:
            return False
        return pr.merged

    def get_open_prs(self) -> List[PullRequest]:
        """Get all open PRs for the configured repo."""
        try:
            data = self._get(f"/repos/{self.repo}/pulls?state=open")
            return [
                PullRequest(
                    number=pr["number"],
                    title=pr["title"],
                    state=pr["state"],
                    merged=pr.get("merged", False),
                    html_url=pr["html_url"],
                    head_ref=pr["head"]["ref"]
                )
                for pr in data
            ]
        except Exception as e:
            print(f"Error fetching open PRs: {e}")
            return []
