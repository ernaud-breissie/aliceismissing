#!/usr/bin/env python3

import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

def run_cmd(cmd, check=False):
    """Run a command and return (success, output)."""
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return False, e.stderr

# Load environment variables
load_dotenv()

try:
    # Configure git with user from .env
    run_cmd(['git', 'config', '--local', 'user.name', os.getenv('user')], check=True)
    run_cmd(['git', 'config', '--local', 'user.email', os.getenv('email')], check=True)

    # Save requirements
    success, requirements = run_cmd(['pip', 'freeze'], check=True)
    with open('request.txt', 'w') as f:
        f.write(requirements)

    # Get current branch
    branch = subprocess.run(['git', 'symbolic-ref', 'HEAD'], 
                          capture_output=True, text=True, check=True).stdout.strip().split('/')[-1]

    # Try to pull, ignore if branch doesn't exist
    run_cmd(['git', 'pull', 'origin', branch])

    # Add all changes
    run_cmd(['git', 'add', '.'], check=True)

    # Create commit with timestamp
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    commit_success, commit_output = run_cmd(['git', 'commit', '-m', f'wip {branch} Updated: {current_time}'])

    # Push only if commit succeeded and there were changes
    if commit_success and "nothing to commit" not in commit_output:
        # Store original URL
        success, original_url = run_cmd(['git', 'remote', 'get-url', 'origin'])
        
        # Configure authentication URL
        auth_url = f"https://{os.getenv('login')}:{os.getenv('github_token')}@github.com/ernaud-breissie/aliceismissing.git"
        run_cmd(['git', 'remote', 'set-url', 'origin', auth_url])
        
        # Push changes
        run_cmd(['git', 'push', '--set-upstream', 'origin', branch], check=True)
        
        # Restore original URL
        run_cmd(['git', 'remote', 'set-url', 'origin', original_url])
        print("Changes committed and pushed successfully")
    else:
        print("No changes to commit")

    # Restore normal git configuration
    run_cmd(['git', 'config', '--local', 'user.name', os.getenv('user_normal')], check=True)
    run_cmd(['git', 'config', '--local', 'user.email', os.getenv('email_normal')], check=True)

except Exception as e:
    print(f"Error: {str(e)}")
    exit(1)
