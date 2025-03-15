#!/bin/bash
# print_code_files.sh
# This script prints the contents of all non-empty, non-binary code files in the project,
# excluding directories such as __pycache__, node_modules, .git, and build.

echo "----------------------------------------------------------------------"
echo "Printing all non-empty, non-binary code files (excluding __pycache__, node_modules, .git, build directories)..."
echo "----------------------------------------------------------------------"

find . \( \
    -path "*/__pycache__" -o \
    -path "*/node_modules" -o \
    -path "*/.git" -o \
    -path "*/build" \
\) -prune -o -type f -size +0c -print | while read -r file; do
    # Check if the file is text (non-binary) using grep -Iq
    if grep -Iq . "$file"; then
        echo "----------------------------------------------------------------------"
        echo "File: $file"
        echo "----------------------------------------------------------------------"
        cat "$file"
        echo ""
    fi
done
