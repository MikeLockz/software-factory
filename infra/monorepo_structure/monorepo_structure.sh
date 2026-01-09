#!/bin/bash

# Script to create a basic monorepo structure

MONOREPO_NAME="my-monorepo"
APPS_DIR="apps"
LIBS_DIR="libs"
TOOLS_DIR="tools"

# Create the monorepo directory
mkdir -p "$MONOREPO_NAME"
cd "$MONOREPO_NAME"

# Initialize git
git init

# Create apps, libs, and tools directories
mkdir -p "$APPS_DIR"
mkdir -p "$LIBS_DIR"
mkdir -p "$TOOLS_DIR"

# Create example app
mkdir -p "$APPS_DIR/my-app"
echo "console.log('Hello from my-app');" > "$APPS_DIR/my-app/index.js"

# Create example lib
mkdir -p "$LIBS_DIR/my-lib"
echo "export function myLibFunction() { return 'Hello from my-lib'; }" > "$LIBS_DIR/my-lib/index.js"

# Create example tool
mkdir -p "$TOOLS_DIR/my-tool"
echo "#!/usr/bin/env node\nconsole.log('Hello from my-tool');" > "$TOOLS_DIR/my-tool/index.js"
chmod +x "$TOOLS_DIR/my-tool/index.js"

# Create a basic README
echo "# $MONOREPO_NAME\n\nA monorepo containing apps, libs, and tools." > README.md

# Create a basic .gitignore
echo "node_modules/\n.DS_Store\n" > .gitignore

# Initialize npm (optional, but common)
npm init -y

echo "Monorepo '$MONOREPO_NAME' created successfully."
