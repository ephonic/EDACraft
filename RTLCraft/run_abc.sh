#!/bin/bash
# Auto-generated ABC synthesis script
set -e
ABC="abc"
if ! command -v "$ABC" &> /dev/null; then
    echo "Error: ABC not found. Please install Berkeley ABC and ensure it is in PATH."
    echo "Installation: https://github.com/berkeley-abc/abc"
    exit 1
fi
"$ABC" -f "/tmp/test.blif.abc"
echo "Synthesis completed: /tmp/test_mapped.v"
