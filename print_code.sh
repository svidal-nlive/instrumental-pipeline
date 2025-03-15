#!/bin/bash
# A revised version of the directory tree and file content printing script with Option 2

# Enable nullglob so that non-matching globs expand to an empty array
shopt -s nullglob

# Default values
include_hidden=false
exclude_pattern=""

# Parse command-line arguments
while getopts "aI:" opt; do
  case ${opt} in
    a)
      include_hidden=true
      ;;
    I)
      exclude_pattern="$OPTARG"
      ;;
    *)
      printf "Usage: %s [-a] [-I exclude_pattern]\n" "$0"
      exit 1
      ;;
  esac
done

# Build the exclusion regex if provided (supporting comma-separated values)
exclude_regex=""
if [ -n "$exclude_pattern" ]; then
  # Replace commas with pipe to allow multiple patterns
  exclude_regex=$(echo "$exclude_pattern" | sed 's/,/|/g')
fi

# Custom tree-like directory printer function
print_tree() {
  local dir="$1"
  local indent="$2"
  local exclude_regex="$3"

  # Build the list of entries based on include_hidden flag
  local entries=()
  if [ "$include_hidden" = true ]; then
    entries=( "$dir"/* "$dir"/.* )
  else
    entries=( "$dir"/* )
  fi

  # Filter out:
  # - The special directories "." and ".."
  # - The script file itself (determined via the script's basename)
  local filtered=()
  local script_name
  script_name=$(basename "$0")
  for entry in "${entries[@]}"; do
    local entry_name
    entry_name=$(basename "$entry")
    [[ "$entry_name" == "." || "$entry_name" == ".." ]] && continue
    [[ "$entry_name" == "$script_name" ]] && continue
    # Exclude entries matching the exclusion regex if provided
    if [ -n "$exclude_regex" ]; then
      if printf "%s\n" "$entry" | grep -Eq "$exclude_regex"; then
        continue
      fi
    fi
    filtered+=("$entry")
  done

  # Process the filtered entries
  local count=${#filtered[@]}
  for i in "${!filtered[@]}"; do
    local entry="${filtered[$i]}"
    local entry_name
    entry_name=$(basename "$entry")
    if [ "$i" -eq $((count - 1)) ]; then
      printf "%s└── %s\n" "$indent" "$entry_name"
      new_indent="${indent}    "
    else
      printf "%s├── %s\n" "$indent" "$entry_name"
      new_indent="${indent}│   "
    fi

    # Recurse into subdirectories
    if [ -d "$entry" ]; then
      print_tree "$entry" "$new_indent" "$exclude_regex"
    fi
  done
}

# Print the directory tree
printf "===== Directory Tree =====\n"
print_tree "." "" "$exclude_regex"
printf "\n"

# Build the find command safely using an array
find_cmd=(find . -type f)

# Exclude hidden files if -a flag is not set
if [ "$include_hidden" = false ]; then
  find_cmd+=(-not -path "*/.*")
fi

# Exclude the script itself by default (using its resolved path if possible)
script_path=$(realpath "$0" 2>/dev/null || echo "$0")
find_cmd+=(-not -path "$script_path")

# Print file contents of text files
printf "===== File Contents =====\n"
if [ -n "$exclude_regex" ]; then
  while IFS= read -r file; do
    if file "$file" | grep -q "text"; then
      printf "===== %s =====\n" "$file"
      cat "$file"
      printf "\n"
    fi
  done < <("${find_cmd[@]}" | grep -Ev "$exclude_regex")
else
  while IFS= read -r file; do
    if file "$file" | grep -q "text"; then
      printf "===== %s =====\n" "$file"
      cat "$file"
      printf "\n"
    fi
  done < <("${find_cmd[@]}")
fi
