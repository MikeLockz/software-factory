# Operations & Deployment

> **Goal:** Production-ready deployment with Docker, CI/CD, and monitoring.

---

## 1. Docker Setup

### 1.1 Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh

# Install Python dependencies
COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent/ ./agent/

# Set Python path
ENV PYTHONPATH=/app

CMD ["python", "agent/poll.py"]
```

### 1.2 Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  factory:
    build: .
    container_name: software-factory
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LINEAR_API_KEY=${LINEAR_API_KEY}
      - LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
      - LANGCHAIN_TRACING_V2=true
      - LANGCHAIN_PROJECT=software-factory
    volumes:
      - ./repos:/repos  # Mount for git operations
      - ~/.gitconfig:/root/.gitconfig:ro
      - ~/.ssh:/root/.ssh:ro
    restart: unless-stopped

  studio:
    build: .
    container_name: langgraph-studio
    ports:
      - "2024:2024"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
    command: ["langgraph", "dev", "--host", "0.0.0.0"]
    volumes:
      - .:/app
```

---

## 2. CI/CD Pipeline

### 2.1 GitHub Actions

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install ruff
      - run: ruff check agent/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r agent/requirements.txt pytest
      - run: |
          cd agent
          pytest tests/ -v --ignore=tests/e2e

  build:
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: software-factory:${{ github.sha }}
```

### 2.2 Deploy Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_KEY }}
          script: |
            cd /opt/software-factory
            git pull
            docker compose pull
            docker compose up -d
```

---

## 3. Secrets Management

### 3.1 Required Secrets

| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | OpenAI API access |
| `LINEAR_API_KEY` | Linear API access |
| `LANGSMITH_API_KEY` | LangSmith tracing |
| `GITHUB_TOKEN` | For PR creation |
| `SLACK_WEBHOOK_URL` | Alert notifications |

### 3.2 Local Development

Use `.env` file (gitignored):

```env
OPENAI_API_KEY=sk-...
LINEAR_API_KEY=lin_api_...
LANGSMITH_API_KEY=lsv2_pt_...
```

### 3.3 Production

Use environment variables or secrets manager:

```bash
# Docker run with env file
docker run --env-file .env software-factory

# Or individual vars
docker run \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e LINEAR_API_KEY=$LINEAR_API_KEY \
  software-factory
```

---

## 4. Monitoring

### 4.1 Structured Logging

Create `agent/logging_config.py`:

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName
        }
        if hasattr(record, "issue_id"):
            log_obj["issue_id"] = record.issue_id
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    logger = logging.getLogger("factory")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    return logger
```

### 4.2 Metrics

```python
from prometheus_client import Counter, Histogram, start_http_server

# Metrics
issues_processed = Counter('factory_issues_processed_total', 'Total issues processed', ['status'])
processing_time = Histogram('factory_processing_seconds', 'Time to process an issue')
llm_calls = Counter('factory_llm_calls_total', 'Total LLM API calls', ['model', 'node'])

# Start metrics server
start_http_server(8000)

# Usage
with processing_time.time():
    result = app.invoke(state)

issues_processed.labels(status=result["status"]).inc()
```

---

## 5. Cost Monitoring

### 5.1 Token Tracking

```python
from langchain_community.callbacks import get_openai_callback

def process_with_cost_tracking(state: AgentState) -> tuple[dict, dict]:
    """Run workflow with cost tracking."""
    with get_openai_callback() as cb:
        result = app.invoke(state)
    
    cost_info = {
        "total_tokens": cb.total_tokens,
        "prompt_tokens": cb.prompt_tokens,
        "completion_tokens": cb.completion_tokens,
        "total_cost": cb.total_cost
    }
    
    return result, cost_info
```

### 5.2 Budget Alerts

```python
import os

DAILY_BUDGET = float(os.getenv("DAILY_BUDGET_USD", "50.0"))
daily_spend = 0.0

def check_budget(cost: float):
    global daily_spend
    daily_spend += cost
    
    if daily_spend > DAILY_BUDGET * 0.8:
        send_alert(f"⚠️ Daily spend at ${daily_spend:.2f} (80% of ${DAILY_BUDGET})", "warning")
    
    if daily_spend > DAILY_BUDGET:
        send_alert(f"🚨 Daily budget exceeded: ${daily_spend:.2f}", "error")
        raise BudgetExceededError("Daily budget exceeded")
```

---

## 6. Makefile Targets

```makefile
# Build Docker image
build:
	docker compose build

# Start services
up:
	docker compose up -d

# View logs
logs:
	docker compose logs -f factory

# Stop services
down:
	docker compose down

# Restart factory
restart:
	docker compose restart factory

# Clean up
clean:
	docker compose down -v
	docker image prune -f
```

---

## 7. Health Endpoint

Add to `agent/health.py`:

```python
from fastapi import FastAPI
from agent.tools.retry import health_check

app = FastAPI()

@app.get("/health")
def health():
    checks = health_check()
    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}

@app.get("/ready")
def ready():
    return {"ready": True}
```

Run with:
```bash
uvicorn agent.health:app --host 0.0.0.0 --port 8080
```
