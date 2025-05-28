#!/usr/bin/env python3

import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

def run_cmd(cmd, check=False):
    """Run a command and ignore errors if check is False."""
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError:
        if check:
            raise

# Load environment variables
load_dotenv()

try:
    # Configure git with user from .env
    run_cmd(['git', 'config', '--local', 'user.name', os.getenv('user')], check=True)
    run_cmd(['git', 'config', '--local', 'user.email', os.getenv('email')], check=True)

    # Save requirements
    requirements = run_cmd(['pip', 'freeze'], check=True)
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
    run_cmd(['git', 'commit', '-m', f'wip {branch} Updated: {current_time}'], check=True)

    # Push changes
    run_cmd(['git', 'push', '--set-upstream', 'origin', branch], check=True)

    # Restore normal git configuration
    run_cmd(['git', 'config', '--local', 'user.name', os.getenv('user_normal')], check=True)
    run_cmd(['git', 'config', '--local', 'user.email', os.getenv('email_normal')], check=True)

    print("Changes committed and pushed successfully")

except Exception as e:
    print(f"Error: {str(e)}")
    exit(1)
