import requests
import sys
import os
from git import Repo, GitCommandError
from git.exc import GitCommandError
from datetime import datetime

class MyGitHub:

    def __init__(self, config, repo_name, repo_dir, mode="sourcehut"):
        self.config = config
        self.token = config['GITHUB_TOKEN']
        self.owner = config['REPO_OWNER']
        self.repo_name = repo_name
        self.mode = mode

        # self.test_connection()
        # sys.exit()

        if self.is_github_action_running():
            print("GitHub actions running. No commit.")
            sys.exit()

        self.repo = Repo(repo_dir)

        self.clean()

        self.origin = self.repo.remote(name='origin')


    def is_github_action_running(self):
        
        if self.mode != "github":
            return False
        
        url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/actions/runs"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            runs = response.json().get('workflow_runs', [])
            for run in runs:
                if run['status'] == 'in_progress':
                    return True
            print("No GitHub actions running")
        else:
            print(f"Error durung actions GitHub test: {response.status_code}")
        return False
    

    def test_connection(self):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print("Connexion réussie au dépôt GitHub.")
            repo_info = response.json()
            print(f"Nom du dépôt : {repo_info['name']}")
            print(f"Description : {repo_info['description']}")
            print(f"URL : {repo_info['html_url']}")
        else:
            print(f"Erreur de connexion au dépôt GitHub: {response.status_code}")
            sys.exit()


    def clean(self):
        # Avant de faire un commit, vérifie s'il y a des actions en cours
        if self.repo.is_dirty(untracked_files=True):
            print("Modifications non commited…")

            # Ajoute toutes les modifications
            self.repo.git.add(all=True)

            # Crée un commit avec un message approprié
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"Auto-commit uncommited files - {now}"
            self.repo.git.commit('-m', commit_message, allow_empty=True)
            print("Auto-commit done, waiting for push…")


    def delete_all_workflow_runs(self):
        base_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/actions/runs"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        while True:
            response = requests.get(base_url, headers=headers)
            if response.status_code == 200:
                runs = response.json().get('workflow_runs', [])
                if not runs:
                    print("Toutes les exécutions de workflows ont été supprimées.")
                    break
                
                for run in runs:
                    run_id = run['id']
                    delete_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/actions/runs/{run_id}"
                    delete_response = requests.delete(delete_url, headers=headers)
                    if delete_response.status_code == 204:
                        print(f"Deleted workflow run {run_id}")
                    else:
                        print(f"Failed to delete workflow run {run_id}: {delete_response.status_code}")
            else:
                print(f"Erreur lors de la récupération des actions GitHub: {response.status_code}")
                break


    def pull(self):
        # Stasher les changements non commitées
        if self.repo.is_dirty(untracked_files=True):
            print("Stashing local changes...")
            self.repo.git.stash('save')

        # Effectuer le pull
        try:
            self.origin.pull('main')
            print("GitHub: Pull completed successfully.")
        except GitCommandError as e:
            print(f"Erreur lors du pull : {e}")
            sys.exit()

        # Restaurer les changements stachés
        if self.repo.git.stash('list'):
            print("Applying stashed changes...")
            self.repo.git.stash('apply')


    def push(self):
        # Créer un commit seulement si des changements sont présents
        if self.repo.index.diff(None) or self.repo.untracked_files:
            self.repo.git.add(all=True)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"Auto-update - {now}"

            try:
                self.repo.git.commit('-m', commit_message, allow_empty=True)
                
                # Pousser les changements
                self.origin.push('main')

                print(f"Github {self.repo_name} commit done")
            except GitCommandError as e:
                print(f"Erreur lors du commit : {e}")
        else:
            print("Aucun changement à committer.")


    def list_github_files(self):
        """
        Utilise l'API GitHub pour lister les fichiers dans le dépôt distant.
        """
        url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/git/trees/main?recursive=1"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            tree = response.json().get('tree', [])
            return [item['path'] for item in tree if item['type'] == 'blob']
        else:
            print(f"Erreur lors de la récupération des fichiers GitHub: {response.status_code}")
            return []
        

    def sync_local_with_github(self):
        """
        Compare la hiérarchie des fichiers locaux avec celle sur GitHub et pousse les fichiers manquants.
        """
        # Lister les fichiers locaux
        local_files = []
        for root, dirs, files in os.walk(self.repo.working_tree_dir):

            # Exclude directories that start with a dot
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:

                if file.startswith('.'):
                    continue

                local_files.append(os.path.relpath(os.path.join(root, file), self.repo.working_tree_dir))

        # Lister les fichiers sur GitHub
        github_files = self.list_github_files()

        # Identifier les fichiers manquants sur GitHub
        files_to_push = set(local_files) - set(github_files)

        if files_to_push:
            print("Fichiers manquants sur GitHub :")
            for file in files_to_push:
                print(f"Ajout de : {file}")

            # Ajouter et committer les fichiers manquants
            for file in files_to_push:
                self.repo.git.add(file, f=True)  # Utilise -f pour forcer l'ajout

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"Ajout de fichiers manquants - {now}"
            self.repo.git.commit('-m', commit_message, allow_empty=True)

            # Pousser les changements
            try:
                self.origin.push('main')
                print(f"Fichiers manquants poussés vers {self.repo_name}.")
            except GitCommandError as e:
                print(f"Erreur lors du push : {e}")

        else:
            print("Aucun fichier manquant à pousser.")


    def sync_and_push(self):
        """
        Synchronise les fichiers locaux avec GitHub et pousse les changements.
        """
        # Lister les fichiers locaux
        local_files = []
        for root, dirs, files in os.walk(self.repo.working_tree_dir):
            # Exclure les répertoires commençant par un point
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not file.startswith('.'):
                    local_files.append(os.path.relpath(os.path.join(root, file), self.repo.working_tree_dir))

        # Lister les fichiers sur GitHub
        github_files = self.list_github_files()

        # Identifier les fichiers manquants sur GitHub
        files_to_push = set(local_files) - set(github_files)

        if files_to_push:
            print("Fichiers manquants sur GitHub :")
            for file in files_to_push:
                print(f"Ajout de : {file}")
                self.repo.git.add(file, f=True)  # Forcer l'ajout des fichiers

        # Ajouter tous les fichiers modifiés ou nouveaux
        if self.repo.index.diff(None) or self.repo.untracked_files:
            self.repo.git.add(all=True)

        # Créer un commit et pousser les changements
        if self.repo.index.diff('HEAD') or files_to_push:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"Auto-update - {now}"
            try:
                self.repo.git.commit('-m', commit_message, allow_empty=True)
                self.origin.push('main')
                print(f"GitHub {self.repo_name} : Synchronisation et push réussis.")
            except GitCommandError as e:
                print(f"Erreur lors du commit ou du push : {e}")
        else:
            print("Aucun changement à synchroniser.")