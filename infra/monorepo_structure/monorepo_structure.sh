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

# Create a basic package.json
echo '{
  "name": "'$MONOREPO_NAME'",
  "version": "0.0.1",
  "private": true,
  "workspaces": [
    "'$APPS_DIR'/*",
    "'$LIBS_DIR'/*",
    "'$TOOLS_DIR'/*"
  ],
  "scripts": {
    "start": "echo \"Starting all apps\"",
    "build": "echo \"Building all apps and libs\"",
    "test": "echo \"Testing all apps and libs\""
  },
  "devDependencies": {
    "eslint": "^8.0.0"
  }
}' > package.json

# Create a basic .gitignore
echo "node_modules/" > .gitignore
echo "dist/" >> .gitignore

# Install dependencies (optional, but recommended)
npm install

echo "Monorepo '$MONOREPO_NAME' created successfully."
