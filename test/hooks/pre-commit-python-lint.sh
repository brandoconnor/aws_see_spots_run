#!/bin/bash

if command flake8 --help > /dev/null 2>&1; then
    flake8 . --max-line-length=200
    exit_status=$?
    if [ $exit_status -eq 0 ]; then
        echo "flake8 linting completed successfully!"
    else
        echo "flake8 linting failed. Exiting."
        exit $exit_status
    fi
else
    echo "flake8 not found on this system... run pip install flake8 to lint this repo in the future."
fi
