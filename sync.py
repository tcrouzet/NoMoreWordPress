import yaml
import json, os
import subprocess
import boto3
from datetime import datetime

os.system('clear')

with open('site.yml', 'r') as file:
    config = yaml.safe_load(file)

# Chemins et identifiants
invalidation_file = os.path.join(config['export'], 'update.json')
output_file_path = os.path.join(config['export'], 'sync.json')

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

exit()

# Analyse de la sortie pour obtenir les fichiers téléchargés
uploads = json.loads(output)['Uploads']

paths = [f"/{upload['Key']}" for upload in uploads]

# Créer l'invalidation batch si des fichiers ont été modifiés
if paths:
    invalidation_batch = {
        'Paths': {
            'Quantity': len(paths),
            'Items': paths
        },
        'CallerReference': datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    }

    # Sauvegarde du fichier JSON
    with open(invalidation_file, 'w') as file:
        json.dump(invalidation_batch, file)

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
