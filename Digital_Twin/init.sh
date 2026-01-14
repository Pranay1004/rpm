#!/bin/bash
# Make scripts executable
chmod +x scripts/*.sh

# Create initial directories
mkdir -p data logs tests

echo "Setup complete! Run 'bash scripts/setup-dev-env.sh' to install dependencies"
