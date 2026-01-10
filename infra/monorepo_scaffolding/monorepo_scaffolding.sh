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
mkdir -p apps/ui apps/api apps/worker infra docs

# Create a basic Makefile
cat > Makefile <<EOF
.PHONY: install lint format typecheck test build deploy

install:
	pnpm install

lint:
	biome check --apply ./apps/ui ./apps/api ./apps/worker

format:
	prettier --write ./

typecheck:
	tsc --noEmit

test:
	vitest run

build:
	pnpm build

deploy:
	# Placeholder for deployment script
	echo "Deployment script needs to be implemented"
EOF

# Create a basic README.md
cat > README.md <<EOF
# $MONOREPO_NAME

Monorepo for LockDev SaaS Starter project.
EOF

# Create a basic .gitignore file
cat > .gitignore <<EOF
node_modules
.env
.DS_Store
/dist
/build
.terraform
terraform.tfstate
terraform.tfstate.backup
.sops.cache
EOF

# Create a basic pnpm-workspace.yaml
cat > pnpm-workspace.yaml <<EOF
packages:
  - 'apps/*'
EOF

# Create a basic pre-commit-config.yaml
cat > .pre-commit-config.yaml <<EOF
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files
    -   id: check-merge-conflict
-   repo: https://github.com/prettier/prettier-pre-commit
    rev: v3.1.0
    hooks:
    -   id: prettier
-   repo: https://github.com/ikamensh/flynt
    rev: 1.0.0
    hooks:
    -   id: flynt

EOF

# Initialize pnpm
pnpm init

# Install prettier, biome, typescript, vitest, pre-commit
pnpm add -D prettier @biomejs/biome typescript vitest pre-commit

# Create a basic tsconfig.json
cat > tsconfig.json <<EOF
{
  "compilerOptions": {
    "target": "esnext",
    "module": "esnext",
    "moduleResolution": "node",
    "jsx": "react-jsx",
    "esModuleInterop": true,
    "strict": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules"]
}
EOF

# Create a basic biome.json
cat > biome.json <<EOF
{
	"$schema": "https://biomejs.dev/schemas/1.5.3/schema.json",
	"organizeImports": {
		"enabled": true
	},
	"linter": {
		"enabled": true,
		"rules": {
			"recommended": true
		}
	},
	"formatter": {
		"enabled": true,
		"formatWithErrors": false,
		"indentStyle": "space",
		"indentWidth": 2,
		"lineWidth": 120
	}
}
EOF

# Initialize pre-commit
pre-commit install

echo "Monorepo scaffolding complete.  Run 'make install' to install dependencies."
