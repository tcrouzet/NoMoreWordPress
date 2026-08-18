# NoMoreWordPress

NoMoreWordPress génère un site statique à partir d’un vault de fichiers
Markdown. Le contenu est écrit dans Obsidian, la configuration est en YAML et
les templates produisent un export HTML autonome. Un même code peut générer
plusieurs sites : le nom passé à la commande sélectionne `sites/<site>.yml`.

## Hiérarchie du projet

```text
NoMoreWordPress/
├── tools/                 scripts Python de lecture, génération et sync
├── templates/<template>/  HTML Liquid, CSS, JavaScript et assets du site
├── sites/                 une configuration YAML par site
├── gen.sh                 activation du venv puis génération
└── sync_md.sh             synchronisation autonome du miroir Markdown
```

Le vault suit une hiérarchie année/mois pour les billets horodatés :

```text
vault/
├── 2026/08/mon-billet.md
├── 727.md                 page à la racine du site
├── page/                  pages non horodatées (selon `pages`)
├── books/                 autre dossier de pages (selon `pages`)
├── _i/                    images référencées par les Markdown
├── static/                fichiers copiés tels quels (si configuré)
└── footer.md              contenu du menu/footer (si utilisé par le template)
```

Les chemins d’images sont relatifs au fichier Markdown, par exemple
`![Paysage](_i/paysage.webp)`. Les pages placées dans les dossiers listés par
`pages` sont traitées comme pages, et non comme billets datés. Les fichiers
Markdown sans date de publication ne sont pas envoyés dans le miroir
`export_github_md`.

## Configuration d’un site

Copier `sites/site_model.yml` vers `sites/<site>.yml`, puis adapter au moins
`vault`, `export`, `canonical_domain` et `templates`. Les chemins peuvent être
absolus ou relatifs au projet selon le script qui les utilise.

Les principales options sont :

| Clé | Rôle |
| --- | --- |
| `build` | `0` : génération incrémentale ; `1` : nouveaux/modifiés ; `2` : régénération complète sans recréer le schéma ; `3` : reconstruction complète de la base et du site. |
| `version` | Version des CSS/JS/assets. En local, `0` produit une version dynamique ; en production, incrémenter après une modification d’asset. |
| `vault` / `vault_img` | Vault source et dossier des images, généralement `_i/`. |
| `export` | Dossier de sortie du site statique. |
| `static_folder` | Dossier du vault copié tel quel vers `export/static/`, avec suppression des fichiers disparus. |
| `images_dir` / `feeds_dir` | Répertoires d’export des images et des flux. |
| `title`, `description`, `home_title`, `canonical_domain` | Métadonnées générales du site et URL canonique. |
| `pages` | Dossiers dont les Markdown deviennent des pages non horodatées. |
| `tags` | Dictionnaire `slug: {title, url}` des rubriques générées. Le slug est la valeur utilisée dans les tags Markdown. |
| `home_exclude` / `home_tags` | Exclusions et rubriques spéciales de la page d’accueil. |
| `no_export` | Données internes à ne pas exporter, par exemple `comments` ou `notes`. |
| `redirects` | Anciennes URL et destinations correspondantes. |
| `header_menu_filter` | Filtre du menu haut, par exemple `bold` pour les entrées marquées en gras dans `footer.md`. |
| `contact` | Paramètres du formulaire de contact. |
| `events` | Valeurs par défaut des données structurées d’événement (`location`, `organizer`, prix). |
| `diaporamas` | Options des diaporamas : `grid_km` et liste `types` (`vtt`, `gravel`, etc.). |
| `export_github_md` | Dépôt miroir Markdown facultatif. Sa présence active `sync_md`. |
| `gemini_export` | Export Gemini facultatif ; si absent, `sync_gmi` n’est pas lancé. |

### Templates

`templates` est une liste : chaque entrée peut définir `name`, `export`,
`domain`, `skip`, `image_max_size`, `image_min_size`, `sizes`,
`infinite_scroll`, `post_per_page`, `jpeg_thumb`, `inline_assets`,
`comments`, `poster`, `code_blocks`, `background_images` et `sync`.

`image_max_size` limite la largeur de la version principale ;
`image_min_size` sert à produire la petite version responsive. Le générateur
conserve les proportions. Les images raster WebP, AVIF, JPEG, PNG et GIF sont
prises en charge ; SVG, PDF et audio sont copiés sans conversion. Pour les
images WebP/AVIF utilisées comme thumbs sociales, `jpeg_thumb: true` crée aussi
une copie JPEG.

## Front matter YAML des Markdown

Un front matter est placé entre deux lignes `---`, au tout début du fichier :

```yaml
---
layout: page
metatitle: "Titre SEO"
metadescription: "Description pour les moteurs de recherche."
permalink: /ma-page/
date: 2026-09-26T06:00:00Z
header_button: Inscription
header_link: https://example.org/inscription
poster: 1
comments: false
---
```

Champs courants : `layout`, `title`, `description`, `metatitle`,
`metadescription`, `permalink`, `date`, `end_date`, `header_title`,
`header_text`, `header_button`, `header_link`, `comments` et
`background`. Les champs inconnus restent disponibles aux templates Liquid.

`date` sert de date d’événement quand elle est future et de date éditoriale
pour les pages qui l’utilisent. Une date passée ne produit pas de données
structurées `Event`. Pour un événement, renseigner aussi `location`,
`organizer`, `offers` ou utiliser les valeurs `events` du site.

## Publication et tags

Un billet horodaté est publié lorsqu’il contient une ligne de tags de la forme
suivante, généralement en dernière ligne :

```markdown
#blog #2026-8-2-12h00
```

Le tag date `#YYYY-M-D-HhMM` fixe la date de publication. Les autres tags
alimentent les pages de rubriques et les menus configurés dans le YAML. Sans
ce tag date, le Markdown peut être traité localement mais n’est pas copié dans
`export_github_md`. Retirer le tag date retire donc le fichier du miroir lors
de la synchronisation.

Les pages non horodatées peuvent également avoir des tags ; elles sont
classées selon leur dossier ou leur `permalink`.

## Images, thumb et arrière-plans

Par défaut, la première image placée juste après le titre devient le thumb du
billet. Pour choisir explicitement une autre image, ajouter `thumb` à son texte
alternatif :

```markdown
![Photo de couverture thumb](_i/couverture.webp)
```

Avec `poster: 1` dans la configuration du template, cette image est utilisée
comme poster sous le titre et retirée du corps du billet ; avec `poster: 0`,
elle reste également dans le contenu. Une image dont l’alt se termine par
`background` est traitée comme image de fond/parallax lorsque le template le
permet :

```markdown
![Paysage background](_i/paysage.webp)
```

Le texte avant `thumb` ou `background` devient la légende interne. Les images
sont redimensionnées à la génération selon les options du template ; leur
rapport largeur/hauteur est conservé.

Les formats Markdown usuels sont acceptés, notamment les tableaux, les notes
de bas de page et les blocs de code. Les balises éditoriales propres au site
peuvent être écrites directement dans le Markdown :

```markdown
{% bouton = [Gravel](/tag/gravel) %}
{% contact %}
```

Le contenu de `footer.md` est utilisé pour le footer et, selon
`header_menu_filter`, pour les entrées du menu haut. Le fichier est donc un
contenu éditorial du vault, pas une option à recopier dans le YAML.

## Commandes

### Générer un site

```sh
python3 ./tools/gen.py tcrouzet
python3 ./tools/gen.py 727
./gen.sh tcrouzet
./gen.sh 727
```

`gen.sh` active le venv seulement si nécessaire et transmet son premier
argument à `gen.py`. Le script ne pousse aucun dépôt Git : la publication reste
une opération séparée, volontaire.

### Synchroniser le miroir Markdown

```sh
./sync_md.sh tcrouzet
./sync_md.sh 727
```

Cette commande utilise `export_github_md`, recopie les Markdown publiés et
supprime ceux qui ne le sont plus. Elle est utile même si la base ne signale
aucune modification.

### Assets statiques

Si `static_folder: "static"` est défini, chaque `gen.py` synchronise
`vault/static/` vers `export/static/` : les fichiers nouveaux ou modifiés sont
copiés et ceux supprimés de la source sont retirés de la cible.

## Import WordPress (historique)

`tools/wp_export.py` et ses paramètres `WP_DB_*`, `OLD_IMG_DIR`, `IMG_SUB_DIR`
et `EXCLUDE` ne servent qu’à une migration historique depuis WordPress. Ils
sont conservés en bas du modèle de configuration pour reproduire une ancienne
importation, mais ne sont nécessaires ni à l’édition Markdown, ni à la
génération quotidienne, ni aux synchronisations.
