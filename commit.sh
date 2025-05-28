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

# Restore normal git configuration
git config --local user.name "$user_normal"
git config --local user.email "$email_normal"

