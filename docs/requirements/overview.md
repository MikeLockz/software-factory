# Project Overview

This is the Software Factory - an agent-based system for automating software development workflows.

## Architecture

The system uses LangGraph to orchestrate multiple specialized agents:

- **Product Manager**: Converts issues into structured PRDs with user stories and acceptance criteria
- **Classifier**: Routes tasks to appropriate specialized agents based on task type
- **Implementation Engineer**: Generates code using Claude Code CLI
- **Infra Engineer**: Handles infrastructure-related tasks
- **Architect**: Designs system architecture and technical specifications

## Tech Stack

### Backend
- Python with FastAPI
- SQLAlchemy with Alembic for database migrations
- Pydantic for data validation

### Frontend
- React with TypeScript
- Vite for build tooling
- TanStack Query/Router/Form
- Shadcn UI components

## Coding Standards

- All code must pass linting (`make lint`)
- TypeScript for frontend, Python for backend
- Use structured logging with Structlog
- Follow existing patterns in the codebase
