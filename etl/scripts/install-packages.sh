#!/bin/bash

# Check if an argument is provided
if [[ -z "$1" ]]; then
  echo "Usage: $0 <path_to_packages>"
  exit 1
fi

# Check if the provided path exists and is a directory
if [[ ! -d "$1" ]]; then
  echo "Error: The path '$1' does not exist or is not a directory."
  exit 1
fi

# Iterate through the files in the provided directory
for package in "$1"/*; do
  if [[ -f "$package" && "$package" == *.whl ]]; then
    echo "Installing package: $package"
    pip install "$package"
  fi
done
