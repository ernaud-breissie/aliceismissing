#!/bin/zsh
set -e

# Check prerequisites
if ! command -v java &> /dev/null; then
    echo "Error: Java is not installed"
    exit 1
fi

if [ ! -f "bfg.jar" ]; then
    echo "Error: bfg.jar not found in current directory"
    exit 1
fi

if [ ! -f "request.txt" ]; then
    echo "Error: request.txt not found in current directory"
    exit 1
fi

if [ ! -d ".git" ]; then
    echo "Error: Not in a git repository"
    exit 1
fi

echo "Starting repository cleaning process..."

# Create a mirror clone
echo "Creating mirror clone..."
git clone --mirror ./ repo-mirror

# Change to the mirror directory
cd repo-mirror

# Run BFG with request.txt
echo "Running BFG..."
java -jar ../bfg.jar --replace-text ../request.txt

# Clean up and optimize
echo "Cleaning and optimizing repository..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo "BFG cleanup completed. Please verify the changes and push if satisfied."
echo "To push changes: cd repo-mirror && git push --force"

