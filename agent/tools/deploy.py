import os
import subprocess
from typing import Tuple, Optional


def deploy_preview(branch: str) -> Tuple[bool, Optional[str]]:
    """Deploy a preview environment for the branch."""
    vercel_token = os.getenv("VERCEL_TOKEN")
    vercel_project = os.getenv("VERCEL_PROJECT")

    if not vercel_token or not vercel_project:
        return False, "VERCEL_TOKEN or VERCEL_PROJECT not set"

    try:
        result = subprocess.run(
            [
                "vercel", "deploy",
                "--token", vercel_token,
                "--confirm",
                "--meta", f"branch={branch}"
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            preview_url = result.stdout.strip().split("\n")[-1]
            return True, preview_url

        return False, result.stderr

    except Exception as e:
        return False, str(e)


def provision_ephemeral_db(branch: str) -> Tuple[bool, Optional[str]]:
    """Provision an ephemeral database branch using Neon."""
    neon_api_key = os.getenv("NEON_API_KEY")
    neon_project = os.getenv("NEON_PROJECT_ID")

    if not neon_api_key:
        return False, "NEON_API_KEY not set"

    try:
        import httpx

        response = httpx.post(
            f"https://console.neon.tech/api/v2/projects/{neon_project}/branches",
            headers={"Authorization": f"Bearer {neon_api_key}"},
            json={"branch": {"name": branch, "parent_id": "main"}}
        )

        if response.status_code == 201:
            data = response.json()
            connection_string = data.get("connection_uri", "provisioned")
            return True, connection_string

        return False, response.text

    except Exception as e:
        return False, str(e)
