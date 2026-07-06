#!/bin/bash
# Run agent evaluation harness against current prompts
# Requires: npx promptfoo (auto-installed if missing)

set -e

cd "$(dirname "$0")/.."

if ! command -v npx &>/dev/null; then
    echo "Error: npx not found. Install Node.js first."
    exit 1
fi

echo "=== Agent Guidance MCP — Evaluation Harness ==="
echo ""

# Run promptfoo against evals/promptfooconfig.yaml
npx --yes promptfoo@latest eval --config evals/promptfooconfig.yaml

echo ""
echo "=== Evaluation complete ==="
echo "View results: npx promptfoo@latest view"
