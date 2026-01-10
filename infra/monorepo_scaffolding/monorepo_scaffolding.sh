#!/bin/bash

# Monorepo directory structure
MONOREPO_NAME="lockdev-saas-starter"
APPS_DIR="apps"
PACKAGES_DIR="packages"
INFRA_DIR="infra"
DOCS_DIR="docs"

# Create the monorepo directory
mkdir -p "$MONOREPO_NAME"
cd "$MONOREPO_NAME"

# Create core directories
mkdir -p "$APPS_DIR"
mkdir -p "$PACKAGES_DIR"
mkdir -p "$INFRA_DIR"
mkdir -p "$DOCS_DIR"

# Create example apps (frontend, backend, worker)
mkdir -p "$APPS_DIR/frontend"
mkdir -p "$APPS_DIR/backend"
mkdir -p "$APPS_DIR/worker"

# Create example packages (ui-components, utils)
mkdir -p "$PACKAGES_DIR/ui-components"
mkdir -p "$PACKAGES_DIR/utils"

# Create infra directories (opentofu, docker)
mkdir -p "$INFRA_DIR/opentofu"
mkdir -p "$INFRA_DIR/docker"

# Create docs directories (requirements, architecture)
mkdir -p "$DOCS_DIR/requirements"
mkdir -p "$DOCS_DIR/architecture"

# Create essential files
touch Makefile
touch README.md
touch .gitignore

# Initialize git repository
git init

# Add initial files to git
git add .

# Create a basic Makefile
cat > Makefile <<EOF
.PHONY: install lint format typecheck build test e2e

install:
	pnpm install

lint:
	biome check --apply ./src

format:
	prettier --write .

typecheck:
	pnpm tsc

build:
	pnpm build

test:
	pnpm test

e2e:
	pnpm playwright test
EOF

# Create a basic .gitignore file
cat > .gitignore <<EOF
node_modules
.DS_Store
.env
.venv
*.log
/dist
/build
/coverage
.terraform
terraform.tfstate
terraform.tfstate.backup
EOF

# Create a basic README.md file
cat > README.md <<EOF
# Lockdev SaaS Starter

A starter kit for building HIPAA-compliant SaaS applications.
EOF

echo "Monorepo scaffolding created in '$MONOREPO_NAME'"
