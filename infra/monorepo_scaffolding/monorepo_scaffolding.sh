#!/usr/bin/env bash

set -euo pipefail

# Define project name
PROJECT_NAME="lockdev-saas-starter"

# Define directories
ROOT_DIR="."
APPS_DIR="${ROOT_DIR}/apps"
PACKAGES_DIR="${ROOT_DIR}/packages"
INFRA_DIR="${ROOT_DIR}/infra"
DOCS_DIR="${ROOT_DIR}/docs"

# Create directories
mkdir -p "${APPS_DIR}"
mkdir -p "${PACKAGES_DIR}"
mkdir -p "${INFRA_DIR}"
mkdir -p "${DOCS_DIR}"

# Create example apps (frontend, backend, worker)
mkdir -p "${APPS_DIR}/frontend"
mkdir -p "${APPS_DIR}/backend"
mkdir -p "${APPS_DIR}/worker"

# Create example packages (ui-components, utils)
mkdir -p "${PACKAGES_DIR}/ui-components"
mkdir -p "${PACKAGES_DIR}/utils"

# Create infra directories (opentofu, aptible)
mkdir -p "${INFRA_DIR}/opentofu"
mkdir -p "${INFRA_DIR}/aptible"

# Create docs directories (requirements, architecture)
mkdir -p "${DOCS_DIR}/requirements"
mkdir -p "${DOCS_DIR}/architecture"

# Create a basic Makefile
cat > "${ROOT_DIR}/Makefile" <<EOF
.PHONY: install build lint format typecheck test

install:
	pnpm install

build:
	pnpm build

lint:
	pnpm lint

format:
	pnpm format

typecheck:
	pnpm typecheck

test:
	pnpm test

.DEFAULT_GOAL := build
EOF

# Create a basic pnpm-workspace.yaml
cat > "${ROOT_DIR}/pnpm-workspace.yaml" <<EOF
packages:
  - 'apps/*'
  - 'packages/*'
EOF

# Create a basic .gitignore
cat > "${ROOT_DIR}/.gitignore" <<EOF
node_modules
.DS_Store
.env
.terraform
terraform.tfstate
terraform.tfstate.backup
.sops.cache
.age
EOF

# Initialize a README.md
cat > "${ROOT_DIR}/README.md" <<EOF
# ${PROJECT_NAME}

A monorepo for the LockDev SaaS Starter project.
EOF

echo "Monorepo scaffolding created."
