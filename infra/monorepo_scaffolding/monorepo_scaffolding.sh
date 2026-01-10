#!/bin/bash

# Monorepo Scaffolding Script

set -euo pipefail

MONOREPO_NAME="lockdev-saas-starter"

# Create the monorepo directory
mkdir -p "$MONOREPO_NAME"
cd "$MONOREPO_NAME"

# Initialize git repository
git init

# Create essential directories
mkdir -p apps/ui
mkdir -p apps/api
mkdir -p apps/worker
mkdir -p packages/shared
mkdir -p infra
mkdir -p docs

# Create basic files
touch apps/ui/README.md
touch apps/api/README.md
touch apps/worker/README.md
touch packages/shared/README.md
touch infra/README.md
touch docs/README.md
touch README.md

# Create a basic Makefile
cat > Makefile <<EOF
.PHONY: install build lint format typecheck test e2e

install:
	pnpm install

build:
	pnpm run build

lint:
	pnpm run lint

format:
	pnpm run format

typecheck:
	pnpm run typecheck

test:
	pnpm run test

e2e:
	pnpm run e2e

EOF

# Create a basic pnpm-workspace.yaml
cat > pnpm-workspace.yaml <<EOF
packages:
  - 'apps/*'
  - 'packages/*'
EOF

# Create a basic .gitignore file
cat > .gitignore <<EOF
node_modules
.DS_Store
.env
.venv
/dist
/build
.turbo
EOF

# Initialize pnpm
pnpm init

# Install basic dependencies (example)
pnpm add -w prettier biome pre-commit typescript playwright vitest

# Create a basic pre-commit config
mkdir -p .git/hooks
cat > .git/hooks/pre-commit <<EOF
#!/bin/sh
set -e

pnpm run format
git add .

pnpm run lint
git add .

pnpm run typecheck

EOF
chmod +x .git/hooks/pre-commit

# Initial commit
git add .
git commit -m "Initial monorepo scaffolding"

echo "Monorepo scaffolding complete in $MONOREPO_NAME"
