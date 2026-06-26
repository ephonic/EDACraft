#!/bin/bash
# Script to restore missing files from original commit
# Run this when network is stable

COMMIT="b43871308897bc9139ba35a5dd54c4b4a6343148"
REPO="ephonic/EDACraft"

echo "Restoring missing files from commit $COMMIT..."

# Get list of all files
curl -s "https://api.github.com/repos/$REPO/git/trees/$COMMIT?recursive=1" | \
python3 -c "
import json, sys
data = json.load(sys.stdin)
for item in data.get('tree', []):
    if item['type'] == 'blob':
        print(item['path'])
" > /tmp/all_files.txt

# Download each file
while IFS= read -r filepath; do
    if [ ! -f "$filepath" ]; then
        dir=$(dirname "$filepath")
        mkdir -p "$dir"
        echo "Fetching: $filepath"
        curl -sL "https://raw.githubusercontent.com/$REPO/$COMMIT/$filepath" -o "$filepath"
    fi
done < /tmp/all_files.txt

echo "Done!"
