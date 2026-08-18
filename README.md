# NoMoreWordPress

Création d'un site à partir d'une hiérarchie de fichiers markdown.

Le site est décrit dans site.yml (renommer le fichier site_model.yml et modifier les paramètres).

Son look est défini par un template dans le dossier templates.

### wp_export.py


Le script se connecte à la base de données MySQL de WordPress, récupère tous les billets et crée une hiérarchie dans MARKDOWN_DIR.
Les tags et catégories se retrouvent en pied de page (et sont directement actifs sous Obsidian).
Les fichiers sont organisés par année et mois.
Les images sont copiées depuis OLD_IMG_DIR dans IMG_SUB_DIR de chacun des mois.
Tous les liens internes commes les liens images sont relatifs (et actifs).

### gen.py

Passer le nom du site en premier argument. Le fichier de configuration
`sites/<site>.yml` sera alors chargé :

```sh
python3 ./tools/gen.py "tcrouzet"
python3 ./tools/gen.py "727"
./gen.sh tcrouzet
./gen.sh 727
```

### sync_md.sh

Synchronise le miroir Markdown configuré par `export_github_md` dans
`sites/<site>.yml`. Ce script peut être lancé indépendamment de la génération
du site : il recopie les fichiers publiés et supprime du miroir ceux qui ne
sont plus publiés (par exemple après la suppression du tag de publication).

```sh
./sync_md.sh tcrouzet
./sync_md.sh 727
```

Le site doit définir `export_github_md` dans son fichier YAML. Contrairement à
`gen.sh`, cette commande est utile lorsque la base n'a pas détecté de
modification mais que le miroir Markdown doit tout de même être nettoyé.
