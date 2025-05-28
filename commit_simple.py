#!/usr/bin/env python3

import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

import os
import shutil # Pour la copie de fichiers (sauvegarde)

def run_cmd(cmd, check=False):
    """Run a command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Command failed: {' '.join(cmd)}")
            print(f"Error output: {e.stderr}")
            raise
        return False, e.stdout, e.stderr

# Load environment variables
load_dotenv()

try:
    # Configure git with user from .env
    run_cmd(['git', 'config', '--local', 'user.name', os.getenv('user')], check=True)
    run_cmd(['git', 'config', '--local', 'user.email', os.getenv('email')], check=True)

    # Save requirements
    success, requirements, _ = run_cmd(['pip', 'freeze'], check=True)
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
    commit_success, commit_output, commit_error = run_cmd(['git', 'commit', '-m', f'wip {branch} Updated: {current_time}'])
    print(f"Commit output: {commit_output or commit_error}")

    # Push only if commit succeeded and there were changes
    if commit_success and "nothing to commit" not in commit_output:
        # Store original URL
        success, original_url, _ = run_cmd(['git', 'remote', 'get-url', 'origin'])
        auth_url = os.getenv("url_git_projet")
        masked_url = auth_url.replace(os.getenv('github_token'), '****')
        print(f"Setting up authenticated URL: {masked_url}")
        run_cmd(['git', 'remote', 'set-url', 'origin', auth_url])
        #write the user , the the email and the url in the .git/config
        with open('.git/config', 'w') as f:
            config="""
                [core]
                    repositoryformatversion = 0
                    filemode = true
                    bare = false
                    logallrefupdates = true
                [remote "origin"]
                    url = git@github.com:ernaud-breissie/aliceismissing.git
                    fetch = +refs/heads/*:refs/remotes/origin/*
                [branch "main"]
                    remote = origin
                    merge = refs/heads/main
                [user]
                    name = {os.getenv('user')}
                    email = {os.getenv('email')}
                """
            config = config.format(user=os.getenv('user'), email=os.getenv('email'))
            config = config.replace("\\n", "\n")
            config = config.format(url=os.getenv("url_git_projet"))
            f.write(config)



        

        # Verify URL was set correctly
        success, current_url, _ = run_cmd(['git', 'remote', 'get-url', 'origin'])
        masked_current = current_url.replace(os.getenv('github_token'), '****')
        print(f"Current remote URL: {masked_current}")
        
        # Push changes
        print(f"Pushing to branch {branch}...")
        success, push_out, push_err = run_cmd(['git', 'push', '--set-upstream', 'origin', branch])
        if success:
            print("Push successful")
        else:
            print("Push failed with error:")
            print(push_err)
            if push_out:
                print("Push output:")
                print(push_out)
        
        # Restore original URL
        run_cmd(['git', 'remote', 'set-url', 'origin', original_url])
        if success:
            print("Changes committed and pushed successfully")
    else:
        print("No changes to commit")

    # Restore normal git configuration
    run_cmd(['git', 'config', '--global', 'user.name', os.getenv('user_normal')], check=True)
    run_cmd(['git', 'config', '--global', 'user.email', os.getenv('email_normal')], check=True)

except Exception as e:
    print(f"Error: {str(e)}")
    exit(1)
