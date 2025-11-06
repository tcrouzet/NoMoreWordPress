import json, os
import subprocess
import boto3
from datetime import datetime, timezone
import tools.tools as tools

class SyncAWS:

    def __init__(self, config):
        self.config = config

    def sync(self):
        # Chemins et identifiants
        invalidation_file = os.path.join(self.config['export'], 'update.json')
        output_file_path = os.path.join(self.config['export'], 'sync.json')
        output_brut_path = os.path.join(self.config['export'], 'sync.txt')

        test = False

        if not test:
            # Exécution de la synchronisation S3
            command = f'aws s3 sync {self.config['export']} s3://{self.config['bucket_name']} --delete --output json'
            print(command)
            # result = subprocess.run(command, shell=True, capture_output=True, text=True)
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = result.stdout
            print("AWS command done")

            # Sauvegarde des fichiers téléchargés en JSON pour une utilisation ultérieure
            with open(output_brut_path, 'w') as file:
                file.write(output)

            # Analyse basique de la sortie
            uploaded_files = []
            deleted_files = []
            for line in output.splitlines():
                if line.startswith("upload:"):
                    path_part = line.split()[-1]
                    uploaded_files.append(path_part)
                if line.startswith("deleted:"):
                    path_part = line.split()[-1]
                    deleted_files.append(path_part)

            # Sauvegarde des fichiers téléchargés en JSON pour une utilisation ultérieure
            with open(output_file_path, 'w') as file:
                json.dump({'upload':uploaded_files, 'deleted': deleted_files}, file)
            
        else:

            with open(output_file_path, 'r') as file:
                data = json.load(file)
                uploaded_files = data['upload']


        #Filtre
        excluded_files = {".DS_Store"}
        excluded_extensions = {".jpeg", ".jpg", ".webp", ".gif", ".png", ".json", ".pdf", ".mp3", ".txt"}

        # Filtrer les fichiers
        uploaded_files = [
            file_path.replace("s3://" + self.config['bucket_name'], "") for file_path in uploaded_files
            if os.path.basename(file_path) not in excluded_files
            and not file_path.endswith(tuple(excluded_extensions))
        ]


        # Créer l'invalidation batch si des fichiers ont été modifiés
        if len(uploaded_files)>0:

            folders = {}
            for file_path in uploaded_files:

                directory = os.path.dirname(file_path)
                base = os.path.basename(file_path)
                if directory in folders:
                    folders[directory].add(base)
                else:
                    folders[directory] = {base}


            #Compte files par dossier racine
            root_dirs = {}
            for directory, files in folders.items():

                root = tools.get_root(directory)
                if root in root_dirs:
                    root_dirs[root] += len(files)
                else:
                    root_dirs[root] = len(files)


            invalidation_paths = set()
            for directory, files in folders.items():

                root = tools.get_root(directory)
                if root == "/":
                    print(root)
                    for file in files:
                        path = "/" + file
                        invalidation_paths.add(path)
                elif root_dirs[root]>0:
                    invalidation_paths.add(f"/{root}/*")

            if len(invalidation_paths)>15:
                invalidation_paths = []
                invalidation_paths.append("/*")

            invalidation_paths = list(invalidation_paths)
            invalidation_batch = {
                'Paths': {
                    'Quantity': len(invalidation_paths),
                    'Items': invalidation_paths
                },
                'CallerReference': datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
            }

            # Sauvegarde du fichier JSON
            with open(invalidation_file, 'w') as file:
                json.dump(invalidation_batch, file, indent=4, sort_keys=True)

            # if test:
            #      exit("Mode test")

            # Utiliser boto3 pour créer l'invalidation CloudFront
            client = boto3.client('cloudfront')
            with open(invalidation_file, 'r') as file:
                invalidation_data = json.load(file)
                response = client.create_invalidation(
                    DistributionId=self.config['distribution_id'],
                    InvalidationBatch=invalidation_data
                )
                #print("Invalidation créée:", response)
                print("Invalidation créée…")
        else:
            print("Aucun fichier modifié, aucune invalidation nécessaire.")
