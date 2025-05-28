#!/usr/bin/env python3

import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv
import sys

def run_command(command, error_message="Command failed"):
    """Execute a command and handle potential errors."""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: {error_message}")
        print(f"Command output: {e.stderr}")
        sys.exit(1)

def get_current_branch():
    """Get the name of the current git branch."""
    return run_command(
        "git symbolic-ref HEAD | sed -e 's,.*/\\(.*\\),\\1,'",
        "Failed to get current branch"
    )

def get_remote_url(login, password):
    """Get the remote URL with credentials."""
    # Get the current remote URL
    remote_url = run_command(
        "git remote get-url origin",
        "Failed to get remote URL"
    )
    
    # Convert SSH URL to HTTPS if necessary
    if remote_url.startswith("git@"):
        remote_url = remote_url.replace(":", "/").replace("git@", "https://")
    
    # Remove existing credentials if present
    if "@" in remote_url:
        remote_url = "https://" + remote_url.split("@")[1]
    
    # Remove 'https://' if present
    remote_url = remote_url.replace("https://", "")
    
    # Create new URL with credentials
    return f"https://{login}:{password}@{remote_url}"

def check_for_changes():
    """Check if there are local changes that need to be stashed."""
    try:
        status = run_command("git status --porcelain")
        return bool(status.strip())
    except Exception:
        return False

def main():
    # Load environment variables
    if not load_dotenv():
        print("Error: .env file not found")
        sys.exit(1)

    # Get credentials from environment
    login = os.getenv("login")
    password = os.getenv("passwd")

    if not login or not password:
        print("Error: GitHub credentials not found in .env file")
        sys.exit(1)

    try:
        # Get current branch
        branch = get_current_branch()
        print(f"Current branch: {branch}")

        # Check for local changes
        has_local_changes = check_for_changes()
        if has_local_changes:
            print("Stashing local changes...")
            run_command("git stash", "Failed to stash local changes")

        # Configure git credentials
        remote_url = get_remote_url(login, password)
        run_command(
            f'git remote set-url origin "{remote_url}"',
            "Failed to set remote URL"
        )

        # Pull latest changes
        print(f"Pulling latest changes from origin/{branch}...")
        pull_output = run_command(
            f"git pull origin {branch}",
            "Failed to pull latest changes"
        )
        print(pull_output if pull_output else "Successfully pulled latest changes")

        # Reset remote URL to HTTPS without credentials
        clean_url = remote_url.replace(f"{login}:{password}@", "")
        run_command(
            f'git remote set-url origin "{clean_url}"',
            "Failed to reset remote URL"
        )

        # Restore local changes if they were stashed
        if has_local_changes:
            print("Restoring local changes...")
            run_command("git stash pop", "Failed to restore local changes")
            print("Local changes restored")

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

