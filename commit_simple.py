#!/usr/bin/env python3

import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

import os
import shutil # Pour la copie de fichiers (sauvegarde)

def remove_newlines_from_file(file_path):
    """
    Supprime tous les caractères de saut de ligne ('\n') d'un fichier.
    Crée une sauvegarde du fichier original avec l'extension .bak avant la modification.

    Args:
        file_path (str): Le chemin vers le fichier à modifier.

    Returns:
        bool: True si l'opération a réussi, False sinon.
    """
    if not os.path.exists(file_path):
        print(f"Erreur : Le fichier '{file_path}' n'existe pas.")
        return False

    backup_path = file_path + ".bak"

    try:
        # 1. Créer une sauvegarde
        shutil.copy2(file_path, backup_path)
        print(f"Sauvegarde de '{file_path}' créée : '{backup_path}'")

        # 2. Lire le contenu du fichier original
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 3. Supprimer les sauts de ligne
        modified_content = content.replace('\\n', '')

        # 4. Écrire le contenu modifié dans le fichier original
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

        print(f"Tous les sauts de ligne ont été supprimés de '{file_path}'.")
        print("ATTENTION : Ce fichier est probablement corrompu pour Git maintenant.")
        print(f"Si besoin, restaurez à partir de '{backup_path}'.")
        return True

    except FileNotFoundError:
        # Devrait être attrapé par la vérification initiale, mais par sécurité
        print(f"Erreur : Le fichier '{file_path}' n'a pas été trouvé pendant l'opération.")
        return False
    except IOError as e:
        print(f"Erreur d'entrée/sortie lors du traitement du fichier '{file_path}': {e}")
        print(f"Vérifiez les permissions ou si le fichier est utilisé par un autre processus.")
        if os.path.exists(backup_path):
             print(f"Une sauvegarde existe à '{backup_path}'.")
        return False
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")
        if os.path.exists(backup_path):
             print(f"Une sauvegarde existe à '{backup_path}'.")
        return False


def clean_url(url):
    """Clean URL from any special characters and validate it."""
    # Remove any whitespace, newlines, or carriage returns
    cleaned = url.strip()
    cleaned = ''.join(c for c in cleaned if c.isprintable() and c != '\n' and c != '\r')
    # Validate URL format
    if not cleaned.startswith('https://'):
        raise ValueError("Invalid URL format")
    return cleaned

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
        original_url = original_url.replace("\n","")
        original_url = original_url.replace("\\n","")
        if original_url[-1] == "\\":
            original_ur = original_url[:-1]
        
        # Configure authentication URL
        auth_url = f"https://{os.getenv('login')}:{os.getenv('github_token')}@github.com/ernaud-breissie/aliceismissing.git"
        # Clean and validate URL
        auth_url = auth_url.replace("\n","")
        auth_url = auth_url.replace("\n","")
        auth_url = clean_url(auth_url)
        #enleve le dernier \ du string auth_url
        if auth_url[-1] == "\\":
            auth_url = auth_url[:-1]
        masked_url = auth_url.replace(os.getenv('github_token'), '****')
        print(f"Setting up authenticated URL: {masked_url}")
        run_cmd(['git', 'remote', 'set-url', 'origin', auth_url])
        
        # Directly clean .git/config file if needed
        with open('.git/config', 'r') as f:
            config = f.read()
        if '\\n' in config:
            with open('.git/config', 'w') as f:
                f.write(config.replace('\n', ''))
        remove_newlines_from_file(".git/config")
        
        # Verify URL was set correctly
        success, current_url, _ = run_cmd(['git', 'remote', 'get-url', 'origin'])
        masked_current = current_url.replace(os.getenv('github_token'), '****')
        print(f"Current remote URL: {masked_current}")
        
        # Push changes
        print(f"Pushing to branch {branch}...")
        success, push_out, push_err = run_cmd(['git', 'push', '--set-upstream', 'origin', branch])
        success, push_out, push_err = run_cmd(['git', 'push', 'origin', branch])
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
    run_cmd(['git', 'config', '--local', 'user.name', os.getenv('user_normal')], check=True)
    run_cmd(['git', 'config', '--local', 'user.email', os.getenv('email_normal')], check=True)

except Exception as e:
    print(f"Error: {str(e)}")
    exit(1)
