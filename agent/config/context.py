"""
Project context loader for agent prompts.
Loads documentation files to provide additional context to agents.
"""
from pathlib import Path
from functools import lru_cache

# Project root is 2 levels up from this file
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Context files to load for agents
CONTEXT_FILES = [
    "docs/requirements/overview.md",
]


@lru_cache(maxsize=1)
def load_project_context() -> str:
    """Load and cache all project context files.
    
    Returns:
        Combined content of all context files, or empty string if none found.
    """
    context_parts = []
    
    for file_path in CONTEXT_FILES:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists():
            content = full_path.read_text().strip()
            if content:
                context_parts.append(f"## {file_path}\n{content}")
    
    if not context_parts:
        return ""
    
    return "# Project Context\n\n" + "\n\n".join(context_parts)


def get_context_for_prompt() -> str:
    """Get project context formatted for inclusion in prompts.
    
    Returns:
        Context string or placeholder message if no context available.
    """
    context = load_project_context()
    if context:
        return f"\n{context}\n"
    return "(No project context available)"
