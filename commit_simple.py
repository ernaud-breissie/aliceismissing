#!/usr/bin/env python3

import os
import subprocess
import shutil  # Pour la copie de fichiers (sauvegarde)
from datetime import datetime
from dotenv import load_dotenv

def run_cmd(cmd, check=False):
    """Run a command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip()
        
        # Détection des erreurs d'authentification
        if "Authentication failed" in error_msg or "fatal: Authentication failed" in error_msg:
            print("\n❌ Erreur d'authentification Git:")
            print("   - Vérifiez votre token GitHub")
            print("   - Assurez-vous que le token a les bonnes permissions")
            print("   - Vérifiez que l'URL du dépôt est correcte")
        elif "fatal: not a git repository" in error_msg:
            print("\n❌ Erreur: Ce répertoire n'est pas un dépôt Git")
        elif "fatal: remote origin already exists" in error_msg:
            print("\n❌ Erreur: La remote 'origin' existe déjà")
        elif "fatal: refusing to merge unrelated histories" in error_msg:
            print("\n❌ Erreur: Les historiques sont incompatibles")
            print("   Utilisez --allow-unrelated-histories pour forcer la fusion")
        elif "fatal: unable to access" in error_msg:
            print("\n❌ Erreur d'accès au dépôt:")
            print("   - Vérifiez votre connexion internet")
            print("   - Vérifiez les permissions du dépôt")
            print("   - Vérifiez l'URL du dépôt")
        
        if check:
            print(f"\nCommande échouée: {' '.join(cmd)}")
            print(f"Message d'erreur: {error_msg}")
            raise
        return False, e.stdout, error_msg

# Load environment variables
load_dotenv()
#load the .env file
with open('.env', 'r') as f:
    for line in f:
        key, value = line.strip().split('=')
        os.environ[key] = value

try:
    #print the local var in the .env file
    print(os.getenv('user'))
    print(os.getenv('email'))
    print(os.getenv('url_git_projet'))
    print(os.getenv('original_url'))
    print(os.getenv('user_temp'))
    print(os.getenv('email_temp'))
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
    # Configuration git
    auth_url = os.getenv("url_git_projet")
    config = f"""[core]
	repositoryformatversion = 0
	filemode = true
	bare = false
	logallrefupdates = true
[remote "origin"]
	url = {auth_url}
	fetch = +refs/heads/*:refs/remotes/origin/*
[branch "main"]
	remote = origin
	merge = refs/heads/main
[user]
	name = {os.getenv('user_temp')}
	email = {os.getenv('email_temp')}
"""
        # Backup the current config
    shutil.copy2('.git/config', '.git/config.bak')
        
        # Write the new config
    with open('.git/config', 'w') as f:
        f.write(config)
    #print the config
    with open('.git/config', 'r') as f:
        print(f.read())


    # Create commit with timestamp
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    commit_success, commit_output, commit_error = run_cmd(['git', 'commit', '-m', f'wip {branch} Updated: {current_time}'])
    print(f"Commit output: {commit_output or commit_error}")

    # Push only if commit succeeded and there were changes
    if commit_success and "nothing to commit" not in commit_output:
        # Store original URL
        success, original_url, _ = run_cmd(['git', 'remote', 'get-url', 'origin'])
        original_url = os.getenv("original_url")

        masked_url = auth_url.replace(os.getenv('github_token'), '****')
        print(f"\n🔧 Configuration de l'URL authentifiée: {masked_url}")
        run_cmd(['git', 'remote', 'set-url', 'origin', auth_url])

        # Verify URL was set correctly
        success, current_url, _ = run_cmd(['git', 'remote', 'get-url', 'origin'])
        masked_current = current_url.replace(os.getenv('github_token'), '****')
        print(f"URL actuelle du remote: {masked_current}")
        
        # Push changes
        print(f"\n⬆️  Push vers la branche {branch}...")
        success, push_out, push_err = run_cmd(['git', 'push', '--set-upstream', 'origin', branch])
        if success:
            print("✅ Push réussi")
        else:
            print("\n❌ Échec du push:")
            print(push_err)
            if push_out:
                print("Sortie du push:")
                print(push_out)
        if success:
            print("\n✅ Changements commités et pushés avec succès")
    else:
        print("\nℹ️  Aucun changement à commiter")

    # Restore normal git configuration
    run_cmd(['git', 'config', '--global', 'user.name', os.getenv('user_normal')], check=True)
    run_cmd(['git', 'config', '--global', 'user.email', os.getenv('email_normal')], check=True)

except Exception as e:
    print(f"\n❌ Erreur critique: {str(e)}")
    print("Stack trace:")
    import traceback
    traceback.print_exc()
    exit(1)
