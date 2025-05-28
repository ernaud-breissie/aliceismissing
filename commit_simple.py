#!/usr/bin/env python3

import os
import subprocess
import shutil
from datetime import datetime
from dotenv import load_dotenv
import re
import pty

def mask_sensitive_data(content):
    """Mask sensitive data in content."""
    # Mask GitHub tokens
    content = re.sub(r'ghp_[a-zA-Z0-9]{36}', 'ghp_****', content)
    # Mask other potential tokens
    content = re.sub(r'[a-zA-Z0-9]{40}', '****', content)
    return content

def handle_git_error(error_msg):
    """Handle Git specific errors and return appropriate message."""
    if "GH013" in error_msg or "Repository rule violations" in error_msg:
        print("\n❌ Erreur: Violation des règles du dépôt GitHub")
        print("   - Des informations sensibles ont été détectées")
        print("   - GitHub a bloqué le push pour des raisons de sécurité")
        print("\n🔍 Actions recommandées:")
        print("   1. Annuler le dernier commit:")
        print("      git reset --hard HEAD~1")
        print("   2. Vérifier les fichiers pour des tokens ou secrets")
        print("   3. Relancer le script")
        return True
    elif "Authentication failed" in error_msg or "fatal: Authentication failed" in error_msg:
        print("\n❌ Erreur d'authentification Git:")
        print("   - Vérifiez votre token GitHub")
        print("   - Assurez-vous que le token a les bonnes permissions")
        print("   - Vérifiez que l'URL du dépôt est correcte")
        return True
    elif "fatal: not a git repository" in error_msg:
        print("\n❌ Erreur: Ce répertoire n'est pas un dépôt Git")
        return True
    elif "fatal: remote origin already exists" in error_msg:
        print("\n❌ Erreur: La remote 'origin' existe déjà")
        return True
    elif "fatal: refusing to merge unrelated histories" in error_msg:
        print("\n❌ Erreur: Les historiques sont incompatibles")
        print("   Utilisez --allow-unrelated-histories pour forcer la fusion")
        return True
    elif "fatal: unable to access" in error_msg:
        print("\n❌ Erreur d'accès au dépôt:")
        print("   - Vérifiez votre connexion internet")
        print("   - Vérifiez les permissions du dépôt")
        print("   - Vérifiez l'URL du dépôt")
        return True
    elif "remote rejected" in error_msg:
        print("\n❌ Erreur: Push rejeté par le dépôt distant")
        print("   - Vérifiez les permissions de la branche")
        print("   - Vérifiez les règles de protection du dépôt")
        print("   - Vérifiez les messages d'erreur ci-dessus")
        return True
    return False

def run_cmd(cmd, check=False):
    """Run a command and return (success, stdout, stderr)."""
    try:
        # Pour les commandes git push, on ne capture pas la sortie pour voir les erreurs en temps réel
        if 'push' in cmd:
            result = subprocess.run(cmd, check=check, text=True)
            return result.returncode == 0, "", ""
        
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip()
        
        # Gestion des erreurs Git spécifiques
        if handle_git_error(error_msg):
            if check:
                print(f"\nCommande échouée: {' '.join(cmd)}")
                print(f"Message d'erreur: {error_msg}")
                raise
            return False, e.stdout, error_msg
        
        # Erreur générique
        if check:
            print(f"\nCommande échouée: {' '.join(cmd)}")
            print(f"Message d'erreur: {error_msg}")
            raise
        return False, e.stdout, error_msg

def backup_git_config():
    """Backup git config and return backup path."""
    backup_path = '.git/config.bak'
    if os.path.exists('.git/config'):
        shutil.copy2('.git/config', backup_path)
        print("✅ Configuration Git sauvegardée")
    return backup_path

def restore_git_config(backup_path):
    """Restore git config from backup."""
    config = f"""[core]
	repositoryformatversion = 0
	filemode = true
	bare = false
	logallrefupdates = true
[remote "origin"]
	url = {original_url}
	fetch = +refs/heads/*:refs/remotes/origin/*
[branch "main"]
	remote = origin
	merge = refs/heads/main
[user]
	name = {os.getenv('user_temp')}
	email = {os.getenv('email_temp')}
"""
    # Backup and update config
    with open('.git/config', 'w') as f:
        f.write(config)
        # restore the origin user and email
        run_cmd(['git', 'config', '--local', 'user.name', os.getenv('user_normal')], check=True)
        run_cmd(['git', 'config', '--local', 'user.email', os.getenv('email_normal')], check=True)

def check_env_variables():
    """Check if all required environment variables are set."""
    required_vars = ['user_temp', 'email_temp', 'url_git_projet', 'github_token']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("\n❌ Erreur: Variables d'environnement manquantes dans le fichier .env")
        print("   Variables manquantes:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n🔍 Actions recommandées:")
        print("   1. Vérifiez que le fichier .env existe")
        print("   2. Ajoutez les variables manquantes dans le fichier .env")
        print("   3. Relancez le script")
        return False
    return True

# Load environment variables
load_dotenv()

# Effacer le fichier de sortie push au début
with open('last_push_output.txt', 'w') as f:
    pass

try:
    # Vérifier les variables d'environnement requises
    if not check_env_variables():
        exit(1)

    print("\n🔧 Configuration initiale...")
    # Configure git with user_temp from .env
    run_cmd(['git', 'config', '--local', 'user.name', os.getenv('user_temp')], check=True)
    run_cmd(['git', 'config', '--local', 'user.email', os.getenv('email_temp')], check=True)

    # Save requirements with sensitive data masked
    print("\n📦 Sauvegarde des dépendances...")
    success, requirements, _ = run_cmd(['pip', 'freeze'], check=True)
    masked_requirements = mask_sensitive_data(requirements)
    with open('request.txt', 'w') as f:
        f.write(masked_requirements)

    # Get current branch
    branch = subprocess.run(['git', 'symbolic-ref', 'HEAD'], 
                          capture_output=True, text=True, check=True).stdout.strip().split('/')[-1]

    # Try to pull, ignore if branch doesn't exist
    print(f"\n⬇️  Mise à jour depuis la branche {branch}...")
    run_cmd(['git', 'pull', 'origin', branch])

    # Add all changes
    print("\n➕ Ajout des modifications...")
    run_cmd(['git', 'add', '.'], check=True)

    # Configuration git
    print("\n⚙️  Configuration du dépôt...")
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
    # Backup and update config
    backup_path = backup_git_config()
    with open('.git/config', 'w') as f:
        f.write(config)

    # Create commit with timestamp
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n💾 Création du commit...")
    commit_success, commit_output, commit_error = run_cmd(['git', 'commit', '-m', f'wip {branch} Updated: {current_time}'])
    print(f"Commit output: {commit_output or commit_error}")

    # Push only if commit succeeded and there were changes
    if commit_success and "nothing to commit" not in commit_output:
        # Store original URL
        success, original_url, _ = run_cmd(['git', 'remote', 'get-url', 'origin'])

        # Mask the token in the URL before displaying
        masked_url = auth_url.replace(os.getenv('github_token'), '****')
        print(f"\n🔧 Configuration de l'URL authentifiée: {masked_url}")
        run_cmd(['git', 'remote', 'set-url', 'origin', auth_url])

        # Verify URL was set correctly
        success, current_url, _ = run_cmd(['git', 'remote', 'get-url', 'origin'])
        masked_current = current_url.replace(os.getenv('github_token'), '****')
        print(f"URL actuelle du remote: {masked_current}")
        
        # Push changes
        print(f"\n⬆️  Push vers la branche {branch}...")
        try:
            # Utiliser pty pour afficher la sortie comme un vrai terminal ET l'écrire dans un fichier
            def read_and_log(fd, log_path):
                with open(log_path, 'a') as logf:
                    while True:
                        try:
                            output = os.read(fd, 1024)
                            if not output:
                                break
                            decoded = output.decode(errors='replace')
                            print(decoded, end='')
                            logf.write(decoded)
                            logf.flush()
                        except OSError:
                            break
            
            pid, fd = pty.fork()
            if pid == 0:
                # Enfant : exécute la commande
                os.execvp('git', ['git', 'push', '--set-upstream', 'origin', branch])
            else:
                # Parent : lit la sortie et log
                read_and_log(fd, 'last_push_output.txt')
                _, status = os.waitpid(pid, 0)
                success = os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0
            
            if not success:
                print("\n❌ Échec du push - Vérifiez les messages d'erreur ci-dessus")
                print("\n🔍 Si vous voyez une erreur GH013 :")
                print("   1. Annuler le dernier commit:")
                print("      git reset --hard HEAD~1")
                print("   2. Vérifier les fichiers pour des tokens ou secrets")
                print("   3. Relancer le script")
            else:
                print("✅ Push réussi")
        except Exception as e:
            print(f"\n❌ Erreur lors du push: {str(e)}")
            success = False
        
        # Restore original URL
        run_cmd(['git', 'remote', 'set-url', 'origin', original_url])

        if success:
            print("\n✅ Changements commités et pushés avec succès")
        else:
            print("\nℹ️  Aucun changement à commiter")

    # Restore git configuration
    restore_git_config(backup_path)

    # Afficher le contenu du fichier de log push à la fin
    print("\n===== Récapitulatif complet du push (last_push_output.txt) =====\n")
    with open('last_push_output.txt', 'r') as f:
        print(f.read())

except Exception as e:
    print(f"\n❌ Erreur critique: {str(e)}")
    print("Stack trace:")
    import traceback
    traceback.print_exc()
    
    # Ensure we restore the config even if there's an error
    if 'backup_path' in locals():
        restore_git_config(backup_path)
    
    exit(1)
