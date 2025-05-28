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

# Debug function for URLs (hiding sensitive info)
debug_url() {
    local url=$1
    echo "${url//$github_token/****}" | sed 's/:[^:@]*@/:****@/'
}

# Clean GitHub token (remove prefix if present)
clean_token() {
    local token=$1
    echo "${token#github_pat_}"
}

# Store original remote URL
original_url=$(git remote get-url origin)
echo "DEBUG: Original remote URL: $(debug_url "$original_url")"

# Extract repository path
if [[ $original_url == *"git@github.com:"* ]]; then
    # Handle SSH URL format
    repo_path=$(echo "$original_url" | sed 's/git@github.com://')
    echo "DEBUG: Extracted repo path from SSH URL: $repo_path"
elif [[ $original_url == *"github.com"* ]]; then
    # Handle HTTPS URL format
    repo_path=$(echo "$original_url" | sed -E 's#^https://([^@]+@)?github.com/##')
    echo "DEBUG: Extracted repo path from HTTPS URL: $repo_path"
fi

# Clean and prepare the token
clean_github_token=$(clean_token "$github_token")
echo "DEBUG: Token cleaned (length: ${#clean_github_token} chars)"

# Configure remote URL with token authentication
auth_url="https://$login:$clean_github_token@github.com/$repo_path"
echo "DEBUG: Setting authenticated URL: $(debug_url "$auth_url")"
git remote set-url origin "$auth_url"

# Verify URL was set correctly
current_url=$(git remote get-url origin)
echo "DEBUG: Current remote URL: $(debug_url "$current_url")"

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
clean_url="https://github.com/$repo_path"
echo "DEBUG: Restoring clean URL: $clean_url"
git remote set-url origin "$clean_url"

# Verify clean URL was set
final_url=$(git remote get-url origin)
echo "DEBUG: Final remote URL: $final_url"

# Restore normal git configuration
git config --local user.name "$user_normal"
git config --local user.email "$email_normal"

