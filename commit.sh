#!/bin/bash

# Load environment variables
source .env

# Configure git with user from .env
git config --local user.name "$user"
git config --local user.email "$email"

# Save requirements
pip freeze > request.txt

# Get current branch
branch=$(git symbolic-ref HEAD | sed -e 's,.*/\(.*\),\1,')

# Store original remote URL
original_url=$(git remote get-url origin)

# Configure remote URL with token authentication
repo_path=$(echo "$original_url" | sed -e 's/https:\/\/github.com\///' -e 's/git@github.com://')
auth_url="https://$login:$github_token@github.com/$repo_path"
git remote set-url origin "$auth_url"

# Pull latest changes
git pull origin $branch

# Stage all changes
git add .

# Create commit with timestamp
current="`date +'%Y-%m-%d %H:%M:%S'`"
msg="Updated: $current"
git commit -m "wip $branch $msg"

# Push changes
git push origin $branch

# Restore original remote URL without credentials
git remote set-url origin "https://github.com/$repo_path"

# Restore normal git configuration
git config --local user.name "$user_normal"
git config --local user.email "$email_normal"

