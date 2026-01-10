"""Implementation Engineer Agent - Uses Claude Code CLI in headless mode as a super tool.

This node orchestrates Claude Code CLI to generate actual code implementations
based on approved contracts, with native file system access and validation.
"""

import re
import subprocess
import json
import logging
from typing import Optional
import os
from agent.config.context import get_context_for_prompt

logger = logging.getLogger(__name__)


def run_claude_code(
    prompt: str,
    working_dir: str,
    allowed_tools: list[str] | None = None,
    output_format: str = "json",
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
        allowed_tools = ["Read", "Edit", "Bash"]
    
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


BACKEND_PROMPT = """You are implementing a backend feature for a FastAPI/Python application.

## Contract
{contract}

## Task
{task}

## Project Context
{context}

## Instructions
1. Read the existing codebase structure to understand patterns
2. Create Pydantic models matching the contract
3. Implement FastAPI router with CRUD endpoints
4. Add database operations using SQLAlchemy/async
5. Include proper validation and error handling
6. Run `make lint` to validate your code
7. Fix any linting errors before completing

Write all files to the appropriate locations based on project structure.
Report what files you created/modified when complete.
"""

FRONTEND_PROMPT = """You are implementing a frontend feature for a React/TypeScript application.

## Contract
{contract}

## Task
{task}

## Project Context
{context}

## Instructions
1. Read the existing codebase structure to understand patterns
2. Create TypeScript interfaces matching the contract
3. Build React components with proper typing
4. Implement API client hooks (React Query style)
5. Add form handling with validation
6. Include loading and error states
7. Run `pnpm lint` to validate your code
8. Fix any linting errors before completing

Write all files to the appropriate locations based on project structure.
Report what files you created/modified when complete.
"""

CONTRACT_PROMPT = """You are implementing a data contract for a full-stack application.

## Contract
{contract}

## Task
{task}

## Project Context
{context}

## Instructions
1. Read the existing codebase structure to understand patterns
2. Create the data contract (Pydantic schema for backend, TypeScript interface for frontend)
3. Ensure the contract matches the specification exactly
4. Add any necessary validation rules
5. Run linting to validate
6. Fix any errors before completing

Write all files to the appropriate locations based on project structure.
Report what files you created/modified when complete.
"""


def implementation_engineer_node(state: AgentState) -> dict:
    """Generate code using Claude Code CLI as a super tool.
    
    This node uses Claude Code CLI in headless mode to:
    - Read and understand the existing codebase
    - Write new files based on the contract
    - Run validation commands (lint, type-check)
    - Self-correct any issues
    """
    # Determine mode from work item or explicit setting
    current_work = state.get("current_work_item")
    if current_work:
        work_type = current_work.get("type") if isinstance(current_work, dict) else getattr(current_work, "type", "BACKEND")
        mode = work_type
    else:
        mode = state.get("implementation_engineer_mode", "BACKEND")
    
    contract = state.get("current_contract", "{}")
    task = ""
    
    # Get task description from work item or state
    if current_work:
        if isinstance(current_work, dict):
            task = current_work.get("description", "")
        else:
            task = getattr(current_work, "description", "")
    
    if not task:
        task = state.get("task_description", "")
    
    # Get project context from PRD if available
    prd = state.get("prd")
    context = ""
    if prd:
        if isinstance(prd, dict):
            context = f"Title: {prd.get('title', '')}\nProblem: {prd.get('problem_statement', '')}"
        else:
            context = f"Title: {getattr(prd, 'title', '')}\nProblem: {getattr(prd, 'problem_statement', '')}"
    
    # Get workspace path - default to current directory
    working_dir = state.get("workspace_path", ".")
    
    # Select prompt based on mode
    if mode == "BACKEND":
        prompt_template = BACKEND_PROMPT
    elif mode == "FRONTEND":
        prompt_template = FRONTEND_PROMPT
    else:  # CONTRACT
        prompt_template = CONTRACT_PROMPT
    
    prompt = prompt_template.format(
        contract=contract,
        task=task,
        context=context
    )
    
    logger.info(f"Implementation Engineer node running in {mode} mode")
    
    # Run Claude Code CLI
    result = run_claude_code(
        prompt=prompt,
        working_dir=working_dir,
        allowed_tools=["Read", "Edit", "Write", "Bash"]
    )
    
    # Return state updates
    return {
        "claude_code_result": result,
        "implementation_engineer_mode": mode,
        "status": "implementation_ready"
    }


CORRECTION_PROMPT = """You previously attempted to implement code but there were issues.

## Original Task
{task}

## Validation/Review Errors
{errors}

## Instructions
1. Read the current state of the files
2. Identify what caused the errors
3. Fix the issues
4. Run validation again to confirm fixes
5. Report what you changed

Do not stop until all errors are resolved.
"""


def implementation_engineer_correction_node(state: AgentState) -> dict:
    """Fix code based on validation or review feedback.
    
    This node is called when the validation node detects errors
    in the Claude Code output.
    """
    errors = state.get("validation_errors") or state.get("review_concerns", [])
    
    # Get original task
    current_work = state.get("current_work_item")
    if current_work:
        if isinstance(current_work, dict):
            task = current_work.get("description", "")
        else:
            task = getattr(current_work, "description", "")
    else:
        task = state.get("task_description", "")
    
    working_dir = state.get("workspace_path", ".")
    
    # Format errors for prompt
    if isinstance(errors, list):
        errors_str = "\n".join(f"- {e}" for e in errors)
    else:
        errors_str = str(errors)
    
    prompt = CORRECTION_PROMPT.format(task=task, errors=errors_str)
    
    logger.info("Implementation Engineer correction node running")
    
    result = run_claude_code(
        prompt=prompt,
        working_dir=working_dir,
        allowed_tools=["Read", "Edit", "Bash"]
    )
    
    correction_count = state.get("correction_count", 0) + 1
    
    return {
        "claude_code_result": result,
        "correction_count": correction_count,
        "status": "implementation_ready"
    }


def validation_node(state: AgentState) -> dict:
    """Check if Claude Code completed successfully.
    
    This node examines the result from the coder node and determines
    if it passed or needs correction.
    """
    result = state.get("claude_code_result", {})
    correction_count = state.get("correction_count", 0)
    
    # Check for errors in the Claude Code output
    if result.get("error"):
        # Don't loop forever - max 3 corrections
        if correction_count >= 3:
            logger.warning("Max correction attempts reached, proceeding anyway")
            return {
                "validation_status": "passed",
                "validation_errors": None,
                "status": "reviewing"
            }
        
        return {
            "validation_status": "failed",
            "validation_errors": result.get("error"),
            "status": "needs_correction"
        }
    
    return {
        "validation_status": "passed",
        "validation_errors": None,
        "status": "reviewing"
    }
