#!/usr/bin/env python3
import re
import sys

def to_snake_case(name):
    # Replace spaces with underscores and lower all letters.
    s = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    return s.replace(" ", "_").lower()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(to_snake_case(sys.argv[1]))
