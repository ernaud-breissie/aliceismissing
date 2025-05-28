#!/usr/bin/env python3

import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv
import sys
from urllib.parse import quote

def run_command(command, error_message="Command failed", check=True):
    """Execute a command and handle potential errors."""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            check=check
        )
        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Error: {error_message}")
            print(f"Command output: {e.stderr}")
            sys.exit(1)
        return ""

def get_current_branch():
    """Get the name of the current git branch."""
    return run_command(
        "git symbolic-ref HEAD | sed -e 's,.*/\\(.*\\),\\1,'",
        "Failed to get current branch"
    )

def save_requirements():
    """Save current pip requirements to request.txt."""
    run_command(
        "pip freeze > request.txt",
        "Failed to save pip requirements"
    )

def is_git_repo():
    """Check if the current directory is a git repository."""
    return run_command("git rev-parse --is-inside-work-tree", check=False) != ""

def has_commits():
    """Check if the repository has any commits."""
    return run_command("git rev-parse --verify HEAD", check=False) != ""

def branch_exists_on_remote(branch):
    """Check if the branch exists on the remote repository."""
    output = run_command(f"git ls-remote --heads origin {branch}", check=False)
    return output.strip() != ""

def configure_git_user(user, email):
    """Configure git user name and email."""
    run_command(f'git config --local user.name "{user}"', "Failed to set git user.name")
    run_command(f'git config --local user.email "{email}"', "Failed to set git user.email")

def restore_git_config(user_normal, email_normal):
    """Restore git configuration to normal user settings."""
    run_command(f'git config --local user.name "{user_normal}"', "Failed to restore git user.name")
    run_command(f'git config --local user.email "{email_normal}"', "Failed to restore git user.email")

def extract_repo_path(url):
    """Extract repository path from GitHub URL."""
    print(f"DEBUG: Extracting repo path from URL: {url}")
    
    # Remove protocol and potential credentials
    clean_url = url.replace("https://", "").replace("http://", "")
    if "@" in clean_url:
        clean_url = clean_url.split("@")[-1]
    
    # Handle SSH format
    if url.startswith("git@github.com:"):
        clean_url = clean_url.replace("git@github.com:", "")
    
    # Extract path after github.com
    if "github.com/" in clean_url:
        parts = clean_url.split("github.com/")
        if len(parts) > 1:
            path = parts[1]
        else:
            raise ValueError(f"Invalid GitHub URL format: {url}")
    elif "github.com:" in clean_url:
        parts = clean_url.split("github.com:")
        if len(parts) > 1:
            path = parts[1]
        else:
            raise ValueError(f"Invalid GitHub URL format: {url}")
    else:
        path = clean_url
    
    # Clean up the path
    path = path.strip("/")
    if not path.endswith(".git"):
        path += ".git"
    
    print(f"DEBUG: Extracted repo path: {path}")
    return path

def get_remote_url(login, token):
    """Get the remote URL with GitHub token authentication using OAuth2 format."""
    print("DEBUG: Getting remote URL with token authentication")

    # Get the current remote URL
    remote_url = run_command(
        "git remote get-url origin",
        "Failed to get remote URL"
    )
    print(f"DEBUG: Current remote URL: {remote_url}")
    
    try:
        # Extract the repository path
        repo_path = extract_repo_path(remote_url)
        
        # Clean up the token by removing any github_pat_ prefix if present
        clean_token = token.replace("github_pat_", "")
        
        # Create new URL with OAuth2 token authentication
        auth_url = f"https://oauth2:{clean_token}@github.com/{repo_path}"
        print(f"DEBUG: Created authenticated URL (token hidden)")
        return auth_url
        
    except ValueError as e:
        print(f"Error processing GitHub URL: {str(e)}")
        sys.exit(1)

def main():
    # Check if we're in a git repository
    if not is_git_repo():
        print("Error: Not in a git repository")
        sys.exit(1)

    # Load environment variables
    if not load_dotenv():
        print("Error: .env file not found")
        sys.exit(1)
    # Get all required variables from environment
    login = os.getenv("login")
    github_token = os.getenv("github_token")
    git_user = os.getenv("user")
    git_email = os.getenv("email")
    user_normal = os.getenv("user_normal")
    email_normal = os.getenv("email_normal")

    # Validate environment variables
    required_vars = {
        'login': login,
        'github_token': github_token,
        'user': git_user,
        'email': git_email,
        'user_normal': user_normal,
        'email_normal': email_normal
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        print("Error: Missing required environment variables")
        print(f"Required variables: {', '.join(required_vars.keys())}")
        sys.exit(1)

    # Configure git user
    configure_git_user(git_user, git_email)

    try:
        # Save pip requirements
        save_requirements()

        # Get current branch
        branch = get_current_branch()

        # Configure git credentials using GitHub token
        remote_url = get_remote_url(login, github_token)
        run_command(
            f'git remote set-url origin "{remote_url}"',
            "Failed to set remote URL"
        )

        # Pull latest changes only if we have commits and branch exists on remote
        if has_commits() and branch_exists_on_remote(branch):
            print("Pulling latest changes...")
            run_command(
                f"git pull origin {branch}",
                "Failed to pull latest changes"
            )
        else:
            print("New repository or branch - skipping pull")

        # Stage all changes
        run_command(
            "git add .",
            "Failed to stage changes"
        )

        # Create commit message with timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        commit_message = f"wip {current_time}"
        
        # Commit changes
        run_command(
            f'git commit -m "{commit_message}"',
            "Failed to commit changes"
        )

        # Push changes, setting upstream for new branches
        push_command = f"git push --set-upstream origin {branch}" if not branch_exists_on_remote(branch) else f"git push origin {branch}"
        run_command(
            push_command,
            "Failed to push changes"
        )
        # Reset remote URL to HTTPS without credentials
        print("DEBUG: Resetting remote URL to clean HTTPS URL")
        # Extract repository path using the same function as before
        repo_path = extract_repo_path(remote_url)
        
        # Create clean HTTPS URL
        clean_url = f"https://github.com/{repo_path}"
        print(f"DEBUG: Clean URL created: {clean_url}")
        run_command(
            f'git remote set-url origin "{clean_url}"',
            "Failed to reset remote URL"
        )

        # Restore git configuration to normal user settings
        restore_git_config(user_normal, email_normal)

        print("Successfully committed and pushed changes")

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

