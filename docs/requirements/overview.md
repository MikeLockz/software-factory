# Software Factory Overview

The Software Factory is an AI-powered development automation system that:

1. **Polls Linear** for issues in the "AI: Ready" state
2. **Generates PRDs** with structured user stories and acceptance criteria
3. **Classifies requests** as contract, infrastructure, or general
4. **Implements code** based on the PRD specifications
5. **Reviews implementations** through security, compliance, and design reviewers
6. **Creates PRs** with meaningful commits and descriptions

## Architecture

- **LangGraph** for workflow orchestration
- **Gemini** for LLM operations
- **Linear** for issue tracking
- **GitHub** for version control and PRs

## Agents

- **Product Manager** - Converts vague ideas into structured PRDs
- **Classifier** - Routes requests to appropriate implementation agents
- **Architect** - Designs contract schemas for API work
- **Software Engineer** - Implements general code changes
- **Infra Engineer** - Handles infrastructure and DevOps tasks
- **Reviewers** - Security, compliance, and design review
- **Publisher** - Creates branches and PRs
