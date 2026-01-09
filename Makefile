.PHONY: agent install lint test poll poll-once

# Run the agent workflow
agent:
	PYTHONPATH=. python agent/main.py

# Install dependencies
install:
	cd agent && pip install -r requirements.txt

# Run linting (install ruff first: pip install ruff)
lint:
	cd agent && ruff check .

# Run tests
test:
	cd agent && pytest tests/ -v

# Poll Linear for issues (continuous loop)
poll:
	PYTHONPATH=. python agent/poll.py

# Run a single poll cycle (no loop)
poll-once:
	PYTHONPATH=. python -c "from agent.poll import poll_and_process; poll_and_process()"
