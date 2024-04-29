import yaml
import json, os
import subprocess
import boto3
from datetime import datetime, timezone

os.system('clear')

with open('site.yml', 'r') as file:
    config = yaml.safe_load(file)

# Chemins et identifiants
invalidation_file = os.path.join(config['export'], 'update.json')
output_file_path = os.path.join(config['export'], 'sync.json')

test = False

if not test:
    # Exécution de la synchronisation S3
    command = f'aws s3 sync {config['export']} s3://{config['bucket_name']}  --delete --output json'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    output = result.stdout

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
excluded_extensions = {".jpeg", ".jpg", ".webp", ".gif", ".png", ".json", ".pdf", ".mp3"}

# Filtrer les fichiers
uploaded_files = [
    file_path for file_path in uploaded_files
    if os.path.basename(file_path) not in excluded_files
    and not file_path.endswith(tuple(excluded_extensions))
]

# Créer l'invalidation batch si des fichiers ont été modifiés
if len(uploaded_files)>0:

    folders = {}
    for file_path in uploaded_files:

        directory = os.path.dirname(file_path).replace("s3://" + config['bucket_name'], "")
        base = os.path.basename(file_path)
        if directory in folders:
            folders[directory].add(base)
        else:
            folders[directory] = {base}


    invalidation_paths = []
    invalidation_dirs = set()
    for directory, files in folders.items():

        parts = directory.split('/')
        if len(parts)>1:
            invalidation_dirs.add((f"/{parts[1]}/*"))

        html = True
        xml = True
        for file in files:
            if file.endswith(".html"):
                if html:
                    invalidation_paths.append(f"{directory}/*.html")
                    html = False
            elif file.endswith(".xml"):
                if xml:
                    invalidation_paths.append(f"{directory}/*.xml")
                    xml = False

            else:
                invalidation_paths.append(f"{directory}/{file}")

    if len(invalidation_paths)>500:
        invalidation_paths = []
        invalidation_paths.append("/*")

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

    if test:
        exit("Mode test")


    # Utiliser boto3 pour créer l'invalidation CloudFront
    client = boto3.client('cloudfront')
    with open(invalidation_file, 'r') as file:
        invalidation_data = json.load(file)
        response = client.create_invalidation(
            DistributionId=config['distribution_id'],
            InvalidationBatch=invalidation_data
        )
        print("Invalidation créée:", response)
else:
    print("Aucun fichier modifié, aucune invalidation nécessaire.")
