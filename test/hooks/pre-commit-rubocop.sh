#!/bin/bash

if command rubocop --help > /dev/null 2>&1; then
    rubocop --config .rubocop_todo.yml
    exit_status=$?
    if [ $exit_status -eq 0 ]; then
        echo "rubocop tests completed successfully!"
    else
        echo "rubocop tests failed. Exiting."
        exit $exit_status
    fi
else
    echo "rubocop not found on this system... run gem install rubocop to check ruby code in the future."
fi
