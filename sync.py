import yaml
import json, os, sys
import subprocess
import boto3
from datetime import datetime
import tools.logs

sys.stdout = tools.logs.DualOutput("_log.txt")
sys.stderr = sys.stdout

os.system('clear')

with open('site.yml', 'r') as file:
    config = yaml.safe_load(file)

# Chemins et identifiants
local_directory = '/Users/thierrycrouzet/Documents/static'
bucket_name = 'tcrouzet.com'
distribution_id = 'E3RIIZ74W6XIH6'
invalidation_file = '/Users/thierrycrouzet/Documents/static/update.json'

# Exécution de la synchronisation S3
command = f'aws s3 sync {local_directory} s3://{bucket_name} --output json'
result = subprocess.run(command, shell=True, capture_output=True, text=True)
output = result.stdout

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
            DistributionId=distribution_id,
            InvalidationBatch=invalidation_data
        )
        print("Invalidation créée:", response)
else:
    print("Aucun fichier modifié, aucune invalidation nécessaire.")
