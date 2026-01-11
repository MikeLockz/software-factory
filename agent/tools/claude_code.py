"""Claude Code CLI wrapper for headless mode execution."""

import subprocess
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def run_claude_code(
    prompt: str,
    working_dir: str = ".",
    allowed_tools: list[str] | None = None,
    output_format: str = "text",
    timeout: int = 300
) -> dict:
    """Execute Claude Code CLI in headless mode.
    
    Args:
        prompt: The task prompt to send to Claude Code.
        working_dir: Directory to run the command in.
        allowed_tools: List of tools to auto-approve (Read, Edit, Write, Bash).
        output_format: Output format - 'json', 'text', or 'stream-json'.
        timeout: Command timeout in seconds.
        
    Returns:
        dict with 'result', 'error', and optionally 'metadata' keys.
    """
    if allowed_tools is None:
        allowed_tools = ["Read"]
    
    cmd = [
        "claude",
        "-p", prompt,
        "--allowedTools", ",".join(allowed_tools),
        "--output-format", output_format
    ]
    
    logger.info(f"Running Claude Code CLI: {' '.join(cmd[:3])}...")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            logger.warning(f"Claude Code exited with code {result.returncode}")
            if result.stderr:
                logger.error(f"Claude Code stderr: {result.stderr}")
            if result.stdout:
                logger.error(f"Claude Code stdout: {result.stdout}")
            return {
                "result": None,
                "error": result.stderr or f"Exit code: {result.returncode}",
                "stdout": result.stdout
            }
        
        if output_format == "json":
            try:
                parsed = json.loads(result.stdout)
                return {
                    "result": parsed.get("result", result.stdout),
                    "error": None,
                    "metadata": parsed.get("metadata", {})
                }
            except json.JSONDecodeError:
                # Claude Code may return plain text even with --output-format json
                return {
                    "result": result.stdout,
                    "error": None
                }
        
        return {"result": result.stdout, "error": result.stderr if result.stderr else None}
        
    except subprocess.TimeoutExpired:
        logger.error(f"Claude Code timed out after {timeout}s")
        return {"result": None, "error": f"Command timed out after {timeout} seconds"}
    except FileNotFoundError:
        logger.error("Claude Code CLI not found - ensure it's installed")
        return {"result": None, "error": "Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code"}
    except Exception as e:
        logger.error(f"Claude Code error: {e}")
        return {"result": None, "error": str(e)}


def extract_json_from_response(response: str) -> dict | None:
    """Extract JSON from a Claude Code response that may contain markdown."""
    import re
    
    # Try to parse directly first
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass
    
    # Try to extract from markdown code block
    if "```" in response:
        # Find JSON code blocks
        json_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass
    
    return None
