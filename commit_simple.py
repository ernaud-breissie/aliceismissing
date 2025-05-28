#!/usr/bin/env python3

import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

def run_cmd(cmd, check=True):
    """Run a command and return output."""
    process = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if check and process.returncode != 0:
        print(f"Error: {process.stderr}")
        exit(1)
    return process.stdout.strip()

def branch_exists(branch):
    """Check if branch exists on remote."""
    result = run_cmd(f"git ls-remote --heads origin {branch}", check=False)
    return bool(result.strip())

def get_repo_path():
    """Extract repository path from current remote URL."""
    url = run_cmd("git remote get-url origin")
    if url.startswith("git@github.com:"):
        return url.replace("git@github.com:", "")
    return url.replace("https://github.com/", "")

def configure_github_url(token=True):
    """Configure remote URL with or without token."""
    repo_path = get_repo_path()
    if token:
        # Set URL with authentication
        auth_url = f"https://{os.getenv('login')}:{os.getenv('github_token')}@github.com/{repo_path}"
        run_cmd(f'git remote set-url origin "{auth_url}"')
    else:
        # Restore clean URL
        clean_url = f"https://github.com/{repo_path}"
        run_cmd(f'git remote set-url origin "{clean_url}"')

# Load environment variables
load_dotenv()

# Configure git with user from .env
run_cmd(f'git config --local user.name "{os.getenv("user")}"')
run_cmd(f'git config --local user.email "{os.getenv("email")}"')

# Save requirements
run_cmd("pip freeze > request.txt")

# Get current branch
branch = run_cmd("git symbolic-ref HEAD | sed -e 's,.*/\\(.*\\),\\1,'")

# Pull latest changes if branch exists
if branch_exists(branch):
    print(f"Pulling latest changes from {branch}...")
    run_cmd(f"git pull origin {branch}")
else:
    print(f"New branch {branch} - skipping pull")

# Add all changes
run_cmd("git add .")

# Create commit with timestamp
current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
run_cmd(f'git commit -m "wip {branch} Updated: {current_time}"')

# Configure GitHub URL with token authentication
configure_github_url(token=True)

# Push changes with upstream for new branches
if branch_exists(branch):
    print(f"Pushing to existing branch {branch}...")
    run_cmd(f"git push origin {branch}")
else:
    print(f"Setting up new branch {branch}...")
    run_cmd(f"git push --set-upstream origin {branch}")

# Restore clean GitHub URL
configure_github_url(token=False)

# Restore normal git configuration
run_cmd(f'git config --local user.name "{os.getenv("user_normal")}"')
run_cmd(f'git config --local user.email "{os.getenv("email_normal")}"')

print("Changes committed and pushed successfully")

