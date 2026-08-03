import sqlite3
import os
import re
import json
import html
import shlex
import datetime
from bs4 import BeautifulSoup
from datetime import date
from urllib.parse import urlparse
import markdown
import frontmatter as ft
import tools
import logs as logs


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)


class Db:

    def __init__(self, config):
        self.config = config
        self.site = config.get('site', 'tcrouzet')
        active_templates = [
            template for template in config.get('templates', [])
            if not template.get('skip', False)
        ]
        self.poster = int(active_templates[0].get('poster', 1)) if active_templates else 1

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.parent_dir = os.path.dirname(script_dir) + os.sep
        script_dir = self.parent_dir

        temp_dir = os.path.join(script_dir, "_temp")
        os.makedirs(temp_dir, exist_ok=True)

        self.db = os.path.join(temp_dir, "posts.db")
        self.conn = sqlite3.connect(self.db)
        self.conn.row_factory = sqlite3.Row

        self.new_posts = 0
        self.updated_posts = 0
        self.deleted_posts = 0
        self.new_tags = 0
        self.updated_tags = 0
        self.used_years = set()

    def test_init(self):
        return "test db ok"

    def create_tables(self, reset=False):
        self.create_table_posts()
        self.create_images_cache()
        self.create_table_tags()
        self.create_table_connectors()

        if reset:
            self.reset_site()

    def reset_site(self):
        """Supprime les données du site courant sans toucher aux autres sites."""
        print(f"Reset posts for site {self.site}")
        c = self.conn.cursor()
        c.execute(
            '''DELETE FROM connectors
               WHERE con_post_id IN (SELECT id FROM posts WHERE site = ?)''',
            (self.site,)
        )
        c.execute('DELETE FROM posts WHERE site = ?', (self.site,))
        c.execute(
            '''DELETE FROM tags
               WHERE NOT EXISTS (
                   SELECT 1 FROM connectors WHERE con_tag_id = tags.tag_id
               )'''
        )
        self.conn.commit()

    def create_table_posts(self, reset=False):
        c = self.conn.cursor()

        if reset:
            print(f"Reset posts for site {self.site}")

        posts_schema = '''CREATE TABLE {table_name} (
            id INTEGER PRIMARY KEY,
            site TEXT NOT NULL DEFAULT 'tcrouzet',
            source_path TEXT,
            title TEXT,
            path_md TEXT UNIQUE,
            pub_date INTEGER,
            pub_update INTEGER,
            thumb_path TEXT DEFAULT '',
            thumb_legend TEXT DEFAULT '',
            type INTEGER CHECK(type IN (0, 1, 2, 4)),  -- 0 post, 1 page, 2 livre, 4 route
            tags TEXT DEFAULT '', -- dic
            url TEXT,
            content TEXT,
            frontmatter TEXT, -- dict json
            description TEXT,
            pub_date_str TEXT,
            pub_update_str TEXT,
            github TEXT,
            tagslist TEXT, -- list json
            datelink TEXT,
            navigation TEXT,  -- dict json
            comments TEXT,
            updated BOOLEAN DEFAULT TRUE
        )'''

        table_sql = c.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'posts'"
        ).fetchone()

        if table_sql:
            columns = {
                row['name'] for row in c.execute('PRAGMA table_info(posts)').fetchall()
            }
            schema_sql = table_sql['sql']
            migration_needed = (
                'site' not in columns
                or 'type IN (0, 1, 2, 4)' not in schema_sql
                or 'path_md TEXT UNIQUE' not in schema_sql
            )

            if migration_needed:
                print("Migration table posts: ajout site et type route")
                c.execute('ALTER TABLE posts RENAME TO posts_legacy')
                c.execute(posts_schema.format(table_name='posts'))

                legacy_columns = {
                    row['name']
                    for row in c.execute('PRAGMA table_info(posts_legacy)').fetchall()
                }
                post_columns = [
                    row['name'] for row in c.execute('PRAGMA table_info(posts)').fetchall()
                    if row['name'] != 'site' or 'site' in legacy_columns
                ]
                select_columns = list(post_columns)

                if 'site' not in legacy_columns:
                    post_columns.insert(1, 'site')
                    select_columns.insert(1, "'tcrouzet'")

                c.execute(
                    f'''INSERT INTO posts ({", ".join(post_columns)})
                        SELECT {", ".join(select_columns)}
                        FROM posts_legacy'''
                )
                c.execute('DROP TABLE posts_legacy')
        else:
            c.execute(posts_schema.format(table_name='posts'))

        # Accélère recherche par path_md
        c.execute('''CREATE INDEX IF NOT EXISTS idx_posts_path ON posts(path_md)''')

        self.conn.commit()

        if reset:
            tables = {
                row['name']
                for row in c.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if {'connectors', 'tags'}.issubset(tables):
                self.reset_site()
            else:
                c.execute('DELETE FROM posts WHERE site = ?', (self.site,))
                self.conn.commit()


    def create_images_cache(self, reset=False):
        """Table pour stocker descriptions images"""
        c = self.conn.cursor()

        if reset:
            print("Reset table images_cache")
            c.execute('DROP TABLE IF EXISTS images_cache')

        c.execute('''CREATE TABLE IF NOT EXISTS images_cache (
            media_source_path TEXT PRIMARY KEY,
            data TEXT
        )''')
        
        self.conn.commit()

    def create_table_tags(self, reset=False):
        """Table pour stocker les tags"""
        c = self.conn.cursor()

        if reset:
            print("Reset table tags")
            c.execute('DROP TABLE IF EXISTS tags')

        c.execute('''CREATE TABLE IF NOT EXISTS tags (
            tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            site TEXT NOT NULL,
            tag_slug TEXT NOT NULL,
            tag_title TEXT NOT NULL,
            tag_url TEXT,
            tag_update INTEGER DEFAULT 0,
            tag_updated BOOLEAN DEFAULT TRUE,
            UNIQUE(site, tag_slug)
        )''')
        
        # Index pour recherche rapide par slug
        c.execute('CREATE INDEX IF NOT EXISTS idx_tags_site_slug ON tags(site, tag_slug)')
        
        self.conn.commit()


    def create_table_connectors(self, reset=False):
        """Table de liaison entre posts et tags (many-to-many)"""
        c = self.conn.cursor()

        if reset:
            print("Reset table connectors")
            c.execute('DROP TABLE IF EXISTS connectors')

        c.execute('''CREATE TABLE IF NOT EXISTS connectors (
            con_tag_id INTEGER NOT NULL,
            con_post_id INTEGER NOT NULL,
            PRIMARY KEY (con_tag_id, con_post_id),
            FOREIGN KEY (con_tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE,
            FOREIGN KEY (con_post_id) REFERENCES posts(id) ON DELETE CASCADE
        )''')
        
        # Index pour recherche rapide par tag (déjà couvert par PRIMARY KEY)
        # Index pour recherche rapide par post
        c.execute('CREATE INDEX IF NOT EXISTS idx_connectors_post ON connectors(con_post_id)')
        
        self.conn.commit()

    def existing_post(self, path_md):
        c = self.conn.cursor()
        c.execute(
            'SELECT id, pub_update FROM posts WHERE site = ? AND path_md = ?',
            (self.site, path_md)
        )
        existing_post = c.fetchone()
        return existing_post

    def insert_post(self, post, existing_post = None):

        post['site'] = self.site

        if 'tags' in post and isinstance(post['tags'], list):
            post['tags'] = json.dumps(post['tags'])
        
        if 'frontmatter' in post and post['frontmatter']:
            post['frontmatter'] = json.dumps(post['frontmatter'], cls=DateTimeEncoder)

        if "tagslist" in post:
            post['tagslist'] = json.dumps(post['tagslist'])

        if not existing_post:
            existing_post = self.existing_post(post['path_md'])

        c = self.conn.cursor()

        if existing_post and post['pub_update'] > existing_post['pub_update']:
            # Update post
            post['id'] = existing_post['id']

            query = '''UPDATE posts SET
                        site = :site,
                        source_path = :source_path,
                        title = :title,
                        pub_date = :pub_date,
                        pub_update = :pub_update,
                        thumb_path = :thumb_path,
                        thumb_legend = :thumb_legend,
                        content = :content,
                        frontmatter = :frontmatter,
                        description = :description,
                        type = :type,
                        tags = :tags,
                        tagslist = :tagslist,
                        url = :url,
                        pub_date_str = :pub_date_str,
                        pub_update_str = :pub_update_str,
                        path_md = :path_md,
                        github = :github,
                        datelink = :datelink,
                        comments = :comments,
                        updated = TRUE
                    WHERE id = :id AND site = :site;'''
            c.execute(query, post)
            self.conn.commit()

            return {"new": 0, "update": 1, "id": existing_post['id']}
        
        elif existing_post and post['pub_update'] <= existing_post['pub_update']:
            #No update

            return {"new": 0, "update": 0, "id": existing_post['id']}
        
        else:
            # New post

            query = '''INSERT INTO posts 
                    (site,  source_path,  title,   path_md,  pub_date,  pub_update,  thumb_path,  thumb_legend,  type,  tags,  content,  frontmatter,  description,  url,  pub_date_str,  pub_update_str,  tagslist,  github,  datelink, comments)
             VALUES (:site, :source_path, :title, :path_md, :pub_date, :pub_update, :thumb_path, :thumb_legend, :type, :tags, :content, :frontmatter, :description, :url, :pub_date_str, :pub_update_str, :tagslist, :github, :datelink, :comments);
            '''
            c.execute(query, post)
            self.conn.commit()
            post_id = c.lastrowid

            if post_id:
                # self.used_tags.update( tags_set )
                date_time = datetime.datetime.fromtimestamp(post['pub_date'])
                self.used_years.add( date_time.year )

                return {"new": 1, "update": 0, "id": post_id}

            else:
                return {"new": 0, "update": 0, "id": None}

    def insert_tag(self, post_id, tagslist, tag_update):
        """
        Insère ou met à jour les tags et crée les liaisons avec le post.
        Retourne {'new': int, 'updated': int, 'linked': int}
        """
        if isinstance(tagslist, str):
            tagslist = json.loads(tagslist)
                
        c = self.conn.cursor()
        stats = {'new': 0, 'updated': 0, 'linked': 0}

        belongs_to_site = c.execute(
            'SELECT 1 FROM posts WHERE id = ? AND site = ?',
            (post_id, self.site)
        ).fetchone()
        if not belongs_to_site:
            return stats

        # Le Markdown est la source de vérité : ses anciennes associations
        # doivent disparaître avant d'enregistrer la nouvelle liste.
        c.execute('DELETE FROM connectors WHERE con_post_id = ?', (post_id,))

        if not tagslist:
            c.execute(
                '''DELETE FROM tags WHERE site = ? AND NOT EXISTS (
                       SELECT 1 FROM connectors WHERE con_tag_id = tags.tag_id
                   )''',
                (self.site,)
            )
            self.conn.commit()
            return stats
        
        for tagdict in tagslist:
            tagdict['tag_update'] = tag_update
            tagdict['site'] = self.site
            
            # Vérifier si le tag existe
            c.execute(
                'SELECT tag_id, tag_update FROM tags WHERE site = ? AND tag_slug = ?',
                (self.site, tagdict['tag_slug'])
            )
            existing_tag = c.fetchone()
            
            if existing_tag and tag_update > existing_tag['tag_update']:
                # UPDATE tag existant
                query = '''UPDATE tags SET
                            tag_title = :tag_title,
                            tag_update = :tag_update,
                            tag_url = :tag_url,
                            tag_updated = TRUE
                        WHERE tag_id = :tag_id AND site = :site'''
                
                tagdict['tag_id'] = existing_tag['tag_id']
                c.execute(query, tagdict)
                tag_id = existing_tag['tag_id']
                stats['updated'] += 1
            
            elif existing_tag:
                # Tag existe, pas de changement
                tag_id = existing_tag['tag_id']
            
            else:
                # INSERT nouveau tag
                query = '''INSERT INTO tags 
                        (site, tag_title, tag_update, tag_slug, tag_url)
                        VALUES (:site, :tag_title, :tag_update, :tag_slug, :tag_url)'''
                c.execute(query, tagdict)
                tag_id = c.lastrowid
                stats['new'] += 1
            
            # Créer la liaison post-tag dans connectors (si pas déjà existante)
            c.execute('''INSERT OR IGNORE INTO connectors (con_tag_id, con_post_id)
                        VALUES (?, ?)''', (tag_id, post_id))
            if c.rowcount > 0:
                stats['linked'] += 1
        
        self.conn.commit()
        return stats

    def sync_config_tags(self):
        """Synchronise titres et URL des tags du site avec le YML courant."""
        c = self.conn.cursor()
        rows = c.execute(
            'SELECT tag_id, tag_slug, tag_title, tag_url FROM tags WHERE site = ?',
            (self.site,)
        ).fetchall()
        changed = 0
        for row in rows:
            expected = self.tag_2_dict(row['tag_slug'])
            if row['tag_title'] == expected['tag_title'] and row['tag_url'] == expected['tag_url']:
                continue
            c.execute(
                '''UPDATE tags SET tag_title = ?, tag_url = ?, tag_updated = TRUE
                   WHERE tag_id = ? AND site = ?''',
                (expected['tag_title'], expected['tag_url'], row['tag_id'], self.site)
            )
            changed += 1
        self.conn.commit()
        self.updated_tags += changed
        return changed

    def updated(self, post):
        try:
            query = '''UPDATE posts SET updated = False WHERE id = ? AND site = ?;'''
            c = self.conn.cursor()

            c.execute(query, (post['id'], self.site))
            self.conn.commit()
            return True
        except Exception as e:
            return False

    def un_updated(self, post_id):
        try:
            query = '''UPDATE posts SET updated = True WHERE id = ? AND site = ?;'''
            c = self.conn.cursor()

            c.execute(query, (post_id, self.site))
            self.conn.commit()
            self.new_posts +=1
            return True
        except Exception as e:
            return False

    def un_updated_by_path(self, md_path):
        try:
            query = '''UPDATE posts SET updated = True WHERE path_md = ? AND site = ?;'''
            c = self.conn.cursor()

            c.execute(query, (md_path, self.site))
            self.conn.commit()
            return True
        except Exception as e:
            return False

    def updated_tag(self, tag):
        try:
            query = '''UPDATE tags
                       SET tag_updated = False
                       WHERE tag_id = ?
                         AND EXISTS (
                             SELECT 1
                             FROM connectors c
                             INNER JOIN posts p ON p.id = c.con_post_id
                             WHERE c.con_tag_id = tags.tag_id AND p.site = ?
                         );'''
            c = self.conn.cursor()

            c.execute(query, (tag['tag_id'], self.site))
            self.conn.commit()
            return True
        except Exception as e:
            return False


    def delete_post(self, post):
        c = self.conn.cursor()

        query = '''DELETE FROM posts WHERE id = ? AND site = ?;'''
        c.execute(query, (post['id'], self.site))
        if c.rowcount > 0:
            return True
        else:
            return False

    def remove_exported_post(self, post):
        """Supprime le fichier HTML généré pour un post disparu du vault."""
        url = (post['url'] or '').strip()
        if not url:
            return

        for template in self.config['templates']:
            export_root = os.path.abspath(template['export'])
            relative_url = url.lstrip('/')
            if relative_url.endswith('.html'):
                target = os.path.abspath(os.path.join(export_root, relative_url))
            else:
                target = os.path.abspath(
                    os.path.join(export_root, relative_url, 'index.html')
                )

            if os.path.commonpath((export_root, target)) != export_root:
                print(f"Refuse deleting outside export: {target}")
                continue

            if os.path.isfile(target):
                os.remove(target)
                print(f"Deleted export: {target}")

                directory = os.path.dirname(target)
                while directory != export_root:
                    try:
                        os.rmdir(directory)
                    except OSError:
                        break
                    directory = os.path.dirname(directory)

    def delete_missing_posts(self, present_paths):
        """Supprime les posts du site courant dont le Markdown n'existe plus."""
        c = self.conn.cursor()
        stored_posts = c.execute(
            'SELECT id, path_md, url FROM posts WHERE site = ?',
            (self.site,)
        ).fetchall()
        missing_posts = [
            post for post in stored_posts if post['path_md'] not in present_paths
        ]

        if not missing_posts:
            return 0

        affected_tag_ids = set()
        for post in missing_posts:
            tag_rows = c.execute(
                'SELECT con_tag_id FROM connectors WHERE con_post_id = ?',
                (post['id'],)
            ).fetchall()
            affected_tag_ids.update(row['con_tag_id'] for row in tag_rows)

            c.execute(
                'DELETE FROM connectors WHERE con_post_id = ?',
                (post['id'],)
            )
            c.execute(
                'DELETE FROM posts WHERE id = ? AND site = ?',
                (post['id'], self.site)
            )
            self.remove_exported_post(post)
            print(f"Deleted from database: {post['path_md']}")

        if affected_tag_ids:
            placeholders = ','.join('?' for _ in affected_tag_ids)
            c.execute(
                f'''UPDATE tags SET tag_updated = TRUE
                    WHERE tag_id IN ({placeholders})''',
                tuple(affected_tag_ids)
            )

        c.execute(
            '''DELETE FROM tags
               WHERE NOT EXISTS (
                   SELECT 1 FROM connectors WHERE con_tag_id = tags.tag_id
               )'''
        )
        self.conn.commit()

        deleted_count = len(missing_posts)
        self.deleted_posts += deleted_count
        self.updated_tags += len(affected_tag_ids)
        return deleted_count

    def db_commit(self):
        self.conn.commit()

    def get_row_factory(self):
        return self.conn.row_factory

    def get_posts(self, condition=None, exclude_tags=None):
        """
        Récupère les posts avec possibilité d'exclusion par tags.
        
        Args:
            condition: Clause WHERE personnalisée (ex: "type=0")
            exclude_tags: Liste de slugs de tags à exclure
        
        Returns:
            Liste des posts
        """
        c = self.conn.cursor()
        
        # Construire la clause WHERE
        where_clause = "WHERE site = ?"
        params = [self.site]
        
        if condition:
            where_clause += f" AND ({condition})"
        
        # Ajouter l'exclusion de tags
        if exclude_tags:
            placeholders = ','.join('?' for _ in exclude_tags)
            exclude_condition = f"id NOT IN (SELECT DISTINCT con_post_id FROM connectors c INNER JOIN tags t ON c.con_tag_id = t.tag_id WHERE t.tag_slug IN ({placeholders}))"
            
            where_clause += f" AND {exclude_condition}"
            params.extend(exclude_tags)
        
        query = f"SELECT *, (COUNT(*) OVER ()) - ROW_NUMBER() OVER (ORDER BY pub_date DESC) + 1 AS ordre FROM posts {where_clause} ORDER BY pub_date DESC"
        
        c.execute(query, tuple(params))
        return c.fetchall()

    def get_post_by_id(self, post_id):
            """
            Récupère un post unique par son ID.
            Retourne le tuple de données du post ou None si non trouvé.
            """
            results = self.get_posts(f"id = {post_id}")
            
            if results:
                return results[0]
            else:
                return None

    def get_posts_updated(self):
        return self.get_posts("updated")

    def get_all_posts(self):
        return self.get_posts("type=0")

    def get_all_posts_and_pages(self):
        return self.get_posts("type<5")


    def get_blog_posts(self, exclude_tags=None):
        """
        Retourne tous les posts de blog (type=0) avec les infos de leur premier tag associé.
        Exclut les posts qui contiennent les tags spécifiés.
        """
        c = self.conn.cursor()
        
        where_clause = "WHERE p.site = ? AND p.type = 0"
        params = [self.site]
        
        if exclude_tags:
            placeholders = ','.join('?' for _ in exclude_tags)
            where_clause += f" AND p.id NOT IN (SELECT DISTINCT c.con_post_id FROM connectors c INNER JOIN tags t ON c.con_tag_id = t.tag_id WHERE t.tag_slug IN ({placeholders}))"
            params.extend(exclude_tags)
        
        query = f'''
            SELECT 
                p.*,
                t.*,
                (COUNT(*) OVER ()) - ROW_NUMBER() OVER (ORDER BY p.pub_date DESC) + 1 AS ordre
            FROM posts p
            LEFT JOIN connectors c ON p.id = c.con_post_id
            LEFT JOIN tags t ON c.con_tag_id = t.tag_id
            {where_clause}
            AND (
                (c.con_tag_id, c.con_post_id) IN (
                    SELECT c2.con_tag_id, c2.con_post_id
                    FROM connectors c2
                    WHERE c2.con_post_id = p.id
                    ORDER BY c2.con_tag_id
                    LIMIT 1
                ) OR c.con_tag_id IS NULL
            )
            GROUP BY p.id
            ORDER BY p.pub_date DESC
        '''
        
        c.execute(query, tuple(params))
        return c.fetchall()


    def get_posts_by_year(self, year, exclude_tags=None):
        """
        Récupère tous les posts d'une année avec le main tag associé.
        Exclut les posts qui contiennent les tags spécifiés.
        """
        c = self.conn.cursor()
        
        where_clause = "WHERE p.site = ? AND strftime('%Y', datetime(p.pub_date, 'unixepoch')) = ? AND p.type = 0"
        params = [self.site, year]
        
        if exclude_tags:
            placeholders = ','.join('?' for _ in exclude_tags)
            where_clause += f" AND p.id NOT IN (SELECT DISTINCT c.con_post_id FROM connectors c INNER JOIN tags t ON c.con_tag_id = t.tag_id WHERE t.tag_slug IN ({placeholders}))"
            params.extend(exclude_tags)
        
        query = f'''
            SELECT 
                p.*,
                t.*,
                (COUNT(*) OVER (PARTITION BY strftime('%Y', datetime(p.pub_date, 'unixepoch')))) - ROW_NUMBER() OVER (PARTITION BY strftime('%Y', datetime(p.pub_date, 'unixepoch')) ORDER BY p.pub_date DESC) + 1 AS ordre
            FROM posts p
            LEFT JOIN connectors c ON p.id = c.con_post_id
            LEFT JOIN tags t ON c.con_tag_id = t.tag_id
            {where_clause}
            AND (
                (c.con_tag_id, c.con_post_id) IN (
                    SELECT c2.con_tag_id, c2.con_post_id
                    FROM connectors c2
                    WHERE c2.con_post_id = p.id
                    ORDER BY c2.con_tag_id
                    LIMIT 1
                ) OR c.con_tag_id IS NULL
            )
            GROUP BY p.id
            ORDER BY p.pub_date DESC
        '''
        
        c.execute(query, tuple(params))
        return c.fetchall()
    
    def get_years(self):
        c = self.conn.cursor()

        query = '''
        SELECT DISTINCT strftime('%Y', datetime(pub_date, 'unixepoch')) AS year
        FROM posts WHERE site = ? AND type = 0
        ORDER BY year DESC
        '''
        c.execute(query, (self.site,))
        years = c.fetchall()

        # years = [year[0] for year in years]
        years = [year[0] for year in years if year[0] != '1970']
        return years

    def get_all_pages(self):
        return self.get_posts("type=1")
    
    def get_post_by_path(self, path):
        c = self.conn.cursor()
        query = f'''
        SELECT * FROM posts
        WHERE site = ? AND path_md = ? LIMIT 1
        '''
        c.execute(query, (self.site, path))
        post = c.fetchone()
        return post

    def get_post_by_title(self, title):
        c = self.conn.cursor()
        query = f'''
        SELECT * FROM posts
        WHERE site = ? AND title = ? LIMIT 1
        '''
        c.execute(query, (self.site, title))
        post = c.fetchone()
        return post


    def get_posts_by_tag(self, tag_slug, limit=None, exclude_tags=None):
        """
        Retourne tous les posts de blog (type=0) d'un tag spécifique avec les infos de leur premier tag associé.
        
        Args:
            tag_slug: Le slug du tag
            limit: Nombre maximum de résultats (None = pas de limite)
            exclude_tags: Liste de slugs de tags à exclure
        """
        c = self.conn.cursor()
        
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        # Condition d'exclusion de tags
        exclude_condition = ""
        params = [self.site, tag_slug]
        
        if exclude_tags:
            placeholders = ','.join('?' for _ in exclude_tags)
            exclude_condition = f"AND p.id NOT IN (SELECT DISTINCT c.con_post_id FROM connectors c INNER JOIN tags t ON c.con_tag_id = t.tag_id WHERE t.tag_slug IN ({placeholders}))"
            params.extend(exclude_tags)
        
        query = f'''
            SELECT 
                p.*,
                t.*,
                (COUNT(*) OVER ()) - ROW_NUMBER() OVER (ORDER BY p.pub_date DESC) + 1 AS ordre
            FROM posts p
            LEFT JOIN connectors c ON p.id = c.con_post_id
            LEFT JOIN tags t ON c.con_tag_id = t.tag_id
            WHERE p.site = ? AND p.id IN (
                SELECT DISTINCT c.con_post_id 
                FROM connectors c 
                INNER JOIN tags t ON c.con_tag_id = t.tag_id 
                WHERE t.tag_slug = ?
            )
            {exclude_condition}
            AND (
                (c.con_tag_id, c.con_post_id) IN (
                    SELECT c2.con_tag_id, c2.con_post_id
                    FROM connectors c2
                    WHERE c2.con_post_id = p.id
                    ORDER BY c2.con_tag_id
                    LIMIT 1
                ) OR c.con_tag_id IS NULL
            )
            GROUP BY p.id
            ORDER BY p.pub_date DESC
            {limit_clause}
        '''
        
        c.execute(query, params)
        return c.fetchall()

    def get_only_posts_by_tag(self, tag_slug, limit=None):
        """
        Retourne tous les contenus d'un tag spécifique.
        
        Args:
            tag_slug: Le slug du tag
            limit: Nombre maximum de résultats (None = pas de limite)
        """
        c = self.conn.cursor()
        
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f'''
            SELECT DISTINCT p.*
            FROM posts p
            INNER JOIN connectors c ON p.id = c.con_post_id
            INNER JOIN tags t ON c.con_tag_id = t.tag_id
            WHERE p.site = ? AND t.tag_slug = ?
            ORDER BY p.pub_date DESC
            {limit_clause}
        '''
        
        c.execute(query, (self.site, tag_slug))
        return c.fetchall()

    def get_last_published_post(self):
        c = self.conn.cursor()
        query = '''
        SELECT * FROM posts
        WHERE site = ?
        ORDER BY pub_date DESC
        LIMIT 1
        '''
        c.execute(query, (self.site,))
        post = c.fetchone()
        return post


    def get_tags_used(self, exclude_slugs=None):
        return self.get_tags(where="WHERE tag_updated = 1", exclude_slugs=exclude_slugs)

    def get_tags(self, order="tag_update DESC", where="", exclude_slugs=None):
        """
        Récupère tous les tags avec possibilité d'exclusion.
        
        Args:
            order: Ordre de tri (par défaut: "tag_update DESC")
            where: Clause WHERE personnalisée
            exclude_tags: Liste de slugs à exclure
        
        Returns:
            Liste des tags
        """
        c = self.conn.cursor()
        
        conditions = [
            '''EXISTS (
                SELECT 1
                FROM connectors c
                INNER JOIN posts p ON p.id = c.con_post_id
                WHERE c.con_tag_id = t.tag_id AND p.site = ?
            )'''
        ]
        params = [self.site]

        if where:
            conditions.append(re.sub(r'^\s*WHERE\s+', '', where, flags=re.IGNORECASE))
        
        if exclude_slugs:
            placeholders = ','.join('?' for _ in exclude_slugs)
            conditions.append(f"t.tag_slug NOT IN ({placeholders})")
            params.extend(exclude_slugs)

        where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f'''
            SELECT t.*, TRUE AS is_tag
            FROM tags t
            {where_clause}
            ORDER BY {order}
        '''
        
        c.execute(query, tuple(params))
        tags = c.fetchall()
        return tags


    def row_to_dict(self, obj):
        row_factory = self.get_row_factory()
        
        if isinstance(obj, row_factory):
            return {key: self.row_to_dict(obj[key]) for key in obj.keys()}
        elif isinstance(obj, (list, tuple)):
            return [self.row_to_dict(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self.row_to_dict(v) for k, v in obj.items()}
        return obj

    def update_fields(self, post_id, fields_dict):
        """
        Met à jour plusieurs champs d'un post.
        Sérialise automatiquement les dict/list en JSON.
        
        Args:
            post_id: ID du post à mettre à jour
            fields_dict: Dictionnaire {nom_colonne: valeur}
        """
        if not fields_dict:
            return True

        try:
            c = self.conn.cursor()
            
            # Préparer les valeurs en sérialisant les dict/list
            processed_values = []
            set_clauses = []
            
            for field_name, value in fields_dict.items():
                # Sérialiser en JSON si dict ou list
                if isinstance(value, (dict, list)):
                    processed_value = json.dumps(value, cls=DateTimeEncoder)
                else:
                    processed_value = value
                
                set_clauses.append(f"{field_name} = ?")
                processed_values.append(processed_value)
            
            # Ajouter l'ID et le site à la fin pour le WHERE
            processed_values.append(post_id)
            processed_values.append(self.site)

            query = f"UPDATE posts SET {', '.join(set_clauses)} WHERE id = ? AND site = ?"
            
            c.execute(query, tuple(processed_values))
            self.conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Erreur update post {post_id}: {e}")
            return False


    def insert_image_cache(self, data_dict):
        """Insère ou met à jour les données d'une image dans le cache
        
        Returns:
            bool: True si succès, False si erreur
        """
        try:
            c = self.conn.cursor()
            
            media_source_path = data_dict['media_source_path']
            data_json = json.dumps(data_dict)
            
            c.execute('''INSERT OR REPLACE INTO images_cache (media_source_path, data) 
                        VALUES (?, ?)''', (media_source_path, data_json))
            
            self.conn.commit()

            return True
            
        except Exception as e:
            print(f"Erreur lors de l'insertion dans images_cache: {e}")
            self.conn.rollback()
            return False

    def get_image_cache(self, template_name, media_source_path):
        # print("get_image_cache")
        try:

            if not media_source_path or media_source_path.endswith("None"):
                return None

            c = self.conn.cursor()
            
            c.execute('SELECT data FROM images_cache WHERE media_source_path = ?', (media_source_path,))
            result = c.fetchone()
            
            if result:
                img_data = json.loads(result[0])
                r = img_data[template_name]
                r['media_size'] = img_data['media_size']
                return r
            else:
                print(f"{media_source_path} not in cache")
            return None
        except Exception as e:
            print(f"Get image cache bug {media_source_path} {template_name}:", e)
            exit()


    def get_tags_with_lastpost(self, exclude_tags=None):
        """
        Retourne tous les tags avec leur dernier post associé (tous les champs).
        """
        c = self.conn.cursor()
        
        where_clause = ""
        params = [self.site, self.site]
        
        if exclude_tags:
            placeholders = ','.join('?' for _ in exclude_tags)
            where_clause = f"AND t.tag_slug NOT IN ({placeholders})"
            params.extend(exclude_tags)
        
        query = f'''
            SELECT 
                t.*,
                p.*,
                COUNT(DISTINCT c.con_post_id) AS post_count
            FROM tags t
            INNER JOIN connectors c ON t.tag_id = c.con_tag_id
            INNER JOIN posts p ON c.con_post_id = p.id
            WHERE p.site = ? AND p.pub_date = (
                SELECT MAX(p2.pub_date)
                FROM posts p2
                INNER JOIN connectors c2 ON p2.id = c2.con_post_id
                WHERE c2.con_tag_id = t.tag_id AND p2.site = ?
            )
            {where_clause}
            GROUP BY t.tag_id
            ORDER BY p.pub_date DESC
        '''
        
        c.execute(query, tuple(params))
        return c.fetchall()

    def list_posts(self, condition=None):
        posts = self.get_posts(condition)
        for post in posts:
            print(dict(post), self.timestamp_to_date(post['pub_date']))
        exit("List end")

    def list_posts_updated(self):
        self.list_posts("updated=1")

    def list_posts_updated(self):
        self.list_posts("updated=1")

    def list_test(self):
        self.list_posts("path_md=null")

    def list_tags(self):
        tags = self.get_tags()
        for tag in tags:
            print(dict(tag))
        exit("List end")

    def list_object(self, objects,exit_flag=True):
        total = len(objects)
        if total == 0:
            exit("Empty")
        else:
            print(total, "objects")
        print(type(objects))
        #objects = dict(objects)
        if isinstance(objects,dict):
            pass
        elif isinstance(objects,list):
            for key, object in enumerate(objects):
                print(key, self.list_object(object))
            exit()
        else:
            objects = dict(objects)
        for key, object in objects.items():
            print(key, object)
        if exit_flag:
            exit()


    ######## Non pure db, externalisable autre classe #######


    def title_formater(self, title):
        return title.capitalize().replace("-"," ").replace("_"," ")

    def filter_tags(self, tags):
        try:
            date_pattern = re.compile(r'^(\d{4})-(\d{1,2})-(\d{1,2})-(\d{1,2})h(\d{1,2})$')  # 'YYYY-M-D-HhM'
            year_pattern = re.compile(r'^y(\d{4})$')  # 'yYYYY'
            filtered_tags = []
            timestamp = 0

            for tag in tags:
                date_match = date_pattern.match(tag)
                if date_match:
                    year, month, day, hour, minute = map(int, date_match.groups())
                    date_obj = datetime.datetime(year, month, day, hour, minute)
                    timestamp = round(date_obj.timestamp())
                elif not year_pattern.match(tag):
                    filtered_tags.append(tag)
            return filtered_tags, timestamp
        except Exception as e:
            print("Error in filter_tags:", e)
            print(tags)
            exit()

    def striptags(self, html_text):
        return re.sub(r'<[^>]+>', '', html_text)
    
    def stripmd(self, markdown_text):
        # Remove images
        markdown_text = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_text)
        # Remove links but keep the text
        markdown_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', markdown_text)
        markdown_text = markdown_text.replace("*","")
        return markdown_text

    def strip_comments(self, markdown_text):
        """Supprime les commentaires au format %%texte%%"""
        markdown_text = re.sub(r'%%.*?%%', '', markdown_text, flags=re.DOTALL)
        return markdown_text

    def resume_paragraph(self, paragraph):
        # Longueur maximale du résumé
        max_length = 160

        c_paragraph = self.striptags(paragraph)
        c_paragraph = self.stripmd(c_paragraph)

        # Si le paragraphe est déjà assez court, le retourner entier
        if len(c_paragraph) <= max_length:
            return c_paragraph
        
        # Couper le paragraphe aux 160 premiers caractères pour trouver un point
        end_index = c_paragraph.rfind('.', 0, max_length)
        
        # Si un point est trouvé dans la limite, retourner jusqu'au point inclus
        if end_index != -1:
            return c_paragraph[:end_index + 1]
        
        # Si aucun point n'est trouvé, couper à 157 caractères et ajouter "..."
        return c_paragraph[:159] + "…"


    def tag_2_dict(self, tag) ->dict:
        if tag in self.config['tags']:
            response = {'tag_slug': tag, "tag_title": self.config['tags'][tag].get('title',tag)}
            turl = self.config['tags'][tag].get("url",None)
            if turl:
                response['tag_url'] = "/" + turl
            else:
                response['tag_url'] = "/tag/" + tag
            response['main'] = True
        else:
            response = {'tag_slug': tag, "tag_title": self.title_formater(tag), "tag_url": "/tag/" + tag, "main": False}
        return response


    def extract_tags(self, tags) ->list:
        
        if len(tags)>1 and "dialogue" in tags:
            tags.remove("dialogue")
        
        #Enrich
        tagslist = []
        main_tag = True
        for tag in tags:
            response = self.tag_2_dict(tag)
            if main_tag and response["main"]:
                tagslist.insert(0, response)
                main_tag = False
            else:
                tagslist.append(response)

        return tagslist


    def get_github_url(self, url):
        github_raw = self.config.get('github_raw')
        if not github_raw:
            return ""
        if not url:
            return ""
        if not url.endswith('/'):
            return ""
        parts = url.strip('/').split('/')
        if len(parts) != 4:
            return ""
        # Si format AAAA/MM/JJ/..., on enlève le "JJ"
        if parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
            parts.pop(2)
        parts[-1] += '.md'
        return github_raw.rstrip('/') + '/' + '/'.join(parts)

    def date_html(self, pub_date) ->str:
        current_time = tools.timestamp_to_paris_datetime(pub_date)
        date_iso = current_time.strftime('%Y-%m-%dT%H:%M:00')
        time_published = current_time.strftime('%H:%M')
        year_link = current_time.strftime('/%Y/')
        day_month = current_time.strftime('%d %B')
        
        msg = f'<a href="{year_link}"><time datetime="{date_iso}" title="Publié à {time_published}">{day_month} {current_time.year}</time></a>'

        return msg

    def is_valid_year_month_path(self, path):
        # Utilisation d'une expression régulière pour tester le format
        pattern = r'^\d{4}/\d{1,2}/'
        return re.match(pattern, path) is not None


    def relative_to_absolute(self, path_md, relative_url, pub_date, post_type):
        
        directory_path = os.path.dirname(path_md)
        full_path = os.path.normpath(os.path.join(directory_path, relative_url.replace(".md","")))
        absolute_path = os.path.abspath(full_path)
        url = os.path.relpath(absolute_path, self.parent_dir).strip("/")

        if self.is_valid_year_month_path(url):
            #C'est un post, faut ajouter le jour
            found_post = self.get_post_by_path(url+".md")
            if found_post:
                url = self.post_url( found_post['path_md'], pub_date, post_type )
            elif "#com" in url:
                #Non géré
                pass
            else:
                pass
                # print("Unknown url", url, "dans:", post['path_md'])
                # exit()
        return "/" + url
    

    def link_manager(self, html, path_md, pub_date, post_type) ->str:

        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a')

        # Canonical domaine (ex: https://tcrouzet.com → tcrouzet.com)
        site_domain = self.config["canonical_domain"]
        site_netloc = urlparse(site_domain if site_domain.startswith("http") else f"https://{site_domain}").netloc

        for link in links:
            href = link.get('href', '')
            if not href:
                continue

            if href.endswith(".md") and not href.startswith("http"):
                #internal
                link['href'] = self.relative_to_absolute(path_md, href, pub_date, post_type)
                continue

            # Liens externes: ajouter rel="noopener noreferrer"
            # on ignore ancres, mailto, tel, etc.
            if href.startswith(("http://", "https://")):
                netloc = urlparse(href).netloc
                if netloc and netloc != site_netloc:
                    existing_rel = link.get("rel", [])
                    # BeautifulSoup normalise rel en liste si présent
                    if isinstance(existing_rel, str):
                        existing_rel = existing_rel.split()
                    # fusion sans doublons
                    rel_tokens = set(existing_rel) | {"noopener", "noreferrer"}
                    link['rel'] = " ".join(sorted(rel_tokens))

        return str(soup)

    def post_url(self, path_md, pub_date, post_type):

        base = os.path.basename(path_md)
        file_name_without_extension = os.path.splitext(base)[0]
        if post_type == 0:

            #POST
            dt = tools.timestamp_to_paris_datetime(pub_date)
            path = dt.strftime("/%Y/%m/%d")
            url = "/" + "/".join([path.strip("/"), file_name_without_extension]) + "/"
        
        else:

            #PAGES
            directory = os.path.dirname(path_md).strip("/")
            url_parts = [part for part in (directory, file_name_without_extension) if part]
            url = "/" + "/".join(url_parts) + "/"

        return url
    
    def comments(self, path_md):
        try:
            source_path = os.path.join(self.config['vault'], self.config['vault_comments'], path_md)
            if os.path.exists(source_path):
                with open(source_path, 'r', encoding='utf-8') as file:
                    content = file.read()
            else:
                return ""

            # Séparer les commentaires par ---
            parts = content.split('---')
            
            # Ignorer la première partie (lien du post)
            comments_list = parts[1:]
            
            html = ''
            
            for i in range(0, len(comments_list), 1):
                part = comments_list[i].strip()
                if not part:
                    continue
                
                lines = part.split('\n')
                if len(lines) < 2:
                    continue
                
                # Première ligne : nom @ date heure
                header = lines[0].strip()
                
                # Extraire nom et date
                if '@' in header:
                    author, datetime_str = header.split('@', 1)
                    author = author.strip()
                    author = author.lstrip("n")
                    datetime_str = datetime_str.strip()
                    datetime_str = ' '.join(datetime_str.split()[:2])
                else:
                    continue
                
                # Récupérer le texte
                text_lines = []
                for line in lines[1:]:
                    text_lines.append(line)
                
                text = '\n'.join(text_lines).strip()
                
                # Générer le HTML
                if text:
                    text = self.to_html(text)
                    html += f'''<h5>{author} @ {datetime_str}</h5>{text}'''

            return html
                    
        except Exception as e:
            exit(f"Bug open comments {e}")
 

    def timestamp_to_date(self, timestamp):
        date_time = datetime.datetime.fromtimestamp(timestamp)
        readable_date = date_time.strftime("%Y-%m-%d")
        return readable_date

    def to_html(self, content):
        content = markdown.markdown(
            content, 
            extensions=['fenced_code', 'pymdownx.mark', 'pymdownx.tilde'],
            extension_configs={
                'fenced_code': {
                    'lang_prefix': ''  # Supprime le préfixe de langage
                }
            }
        )
        return content

    def route_include_to_html(self, content, frontmatter=None):
        """
        Convertit les cartouches courts et les anciens includes `route.html`.
        Les paramètres de l'include sont prioritaires sur les clés `r_*`
        du frontmatter.
        """
        pattern = re.compile(
            r'''{%\s*(?:
                include\s+route\.html\b(?P<legacy>.*?)
                |
                (?P<short>
                    (?:
                        (?:distance|dev|portage|altitude|asphalte|single)
                        \s*=\s*(?:"[^"]*"|'[^']*')\s*
                    )+
                )
            )%}''',
            flags=re.DOTALL | re.VERBOSE
        )
        frontmatter = frontmatter or {}
        icon_base = '/assets/img/route/'
        fields = (
            ('distance', 'r_distance', 'Distance', 'route-distance.svg'),
            ('dev', 'r_dev', 'Dénivelé', 'route-dev.svg'),
            ('portage', 'r_portage', 'Portage', 'route-portage.svg'),
            ('altitude', 'r_altitude', 'Altitude max', 'route-altitude.svg'),
            ('asphalte', 'r_asphalte', 'Asphalte', 'route-asphalte.svg'),
            ('single', 'r_single', 'Singles', 'route-single.svg'),
        )

        def render(match):
            values = {}
            arguments = (
                match.group('legacy')
                if match.group('legacy') is not None
                else match.group('short')
            )
            try:
                for argument in shlex.split(arguments):
                    if '=' in argument:
                        key, value = argument.split('=', 1)
                        values[key.strip()] = value.strip()
            except ValueError as error:
                print(f"Include route.html invalide: {error}")
                return match.group(0)

            stats = []
            for key, fallback_key, label, icon_file in fields:
                value = values.get(key) or frontmatter.get(fallback_key)
                if value in (None, ''):
                    continue
                stats.append(
                    '<div class="route-stat">'
                    f'<img class="route-stat-icon" src="{icon_base}{icon_file}" '
                    'alt="" loading="lazy" decoding="async">'
                    '<span class="route-stat-copy">'
                    f'<span>{html.escape(label)}</span>'
                    f'<strong>{html.escape(str(value))}</strong>'
                    '</span>'
                    '</div>'
                )

            if not stats:
                return ''

            return (
                '<section class="route-summary" aria-label="Caractéristiques de la route">'
                + ''.join(stats)
                + '</section>'
            )

        return pattern.sub(render, content)

    def normalise_md(self, content):
        """
        Normalise la hiérarchie des titres Markdown pour éviter les sauts de niveaux.
        Si pas de h2, décale tout (h3->h2, h4->h3, etc.)
        Sinon, assure une hiérarchie stricte sans sauts.
        """
        # Trouver tous les titres avec leur niveau
        pattern = r'^(#{2,6})\s+(.+)$'
        lines = content.split('\n')
        
        # Identifier les niveaux présents
        levels_present = set()
        for line in lines:
            match = re.match(pattern, line)
            if match:
                level = len(match.group(1))
                levels_present.add(level)
        
        if not levels_present:
            return content
        
        # Créer un mapping de normalisation
        sorted_levels = sorted(levels_present)
        
        # Si pas de h2, on décale tout de -1
        if 2 not in sorted_levels:
            level_mapping = {level: level - 1 for level in sorted_levels}
        else:
            # Sinon, on crée une hiérarchie stricte à partir de h2
            level_mapping = {}
            target_level = 2
            for level in sorted_levels:
                level_mapping[level] = target_level
                target_level += 1
        
        # Appliquer la transformation
        result_lines = []
        for line in lines:
            match = re.match(pattern, line)
            if match:
                current_level = len(match.group(1))
                new_level = level_mapping[current_level]
                title_text = match.group(2)
                result_lines.append('#' * new_level + ' ' + title_text)
            else:
                result_lines.append(line)
        
        return '\n'.join(result_lines)

    def markdown_extract(self, path, path_md, pub_update):
        """
        Extrait toutes les métadonnées et le contenu d'un fichier markdown en un seul passage.
        Retourne: dict avec pub_date, pub_update, title, tags, thumb_path, thumb_legend, 
                content, description, frontmatter
        """
        pub_date = 0        
        title = None
        title_just_found = False
        tags = []
        tagslist = []
        thumb_path = None
        thumb_legend = None
        frontmatter = None
        frontmatter_lines = []
        content = None
        content_lines = []
        thumb_found = False
        first_image = True

        if path_md.startswith('routes'):
            post_type = 4
        elif path_md.startswith('books'):
            post_type = 2
        elif (
            os.path.dirname(path_md) == ''
            or any(path_md.startswith(prefix) for prefix in self.config['pages'])
        ):
            post_type = 1
        else:
            post_type = 0
        
        try:
            with open(path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            in_frontmatter = False
            title_found = False
            
            i = 0
            while i < len(lines):
                line = lines[i]
                # Espace fine
                line = line.replace('\u00A0', '\u202F')
                
                # Détection frontmatter (première ligne)
                if i == 0 and line.strip().startswith('---'):
                    in_frontmatter = True
                    i += 1
                    continue
                
                # Dans le frontmatter
                if in_frontmatter:
                    if line.strip().startswith('---'):
                        in_frontmatter = False
                        frontmatter = ft.Frontmatter(frontmatter_lines)()
                    else:
                        frontmatter_lines.append(line)
                    i += 1
                    continue
                
                # Extraction du titre
                if line.startswith('# ') and title == None:
                    title = line.strip('# ').strip()
                    title_just_found = True
                    i += 1
                    # Ignorer les lignes vides après le titre
                    while i < len(lines) and lines[i].strip() == '':
                        i += 1
                    continue
                
                # Extraction des tags, y compris un tag date seul.
                if line.startswith('#'):
                    potential_tags = line.strip().split()
                    if potential_tags and all(
                        tag.startswith('#') and len(tag) > 1
                        for tag in potential_tags
                    ):
                        tags = [tag[1:] for tag in potential_tags if tag.startswith('#')]
                        tags, pub_date = self.filter_tags(tags)
                        # Ne pas ajouter cette ligne au contenu
                        i += 1
                        continue
                
                # Extraction du thumb
                if '![' in line and not thumb_found:
                    # match = re.search(r'!\[(.*?)\]\((.*?)\)', line)
                    match = re.search(r'(?:\[)?!\[(.*?)\]\((.*?)\)(?:\]\((.*?)\))?', line)
                    if match:
                        # Supprimer la première image du contenu si juste après le titre
                        if (
                            first_image
                            and title_just_found
                            and not match.group(1).endswith(" background")
                        ):
                            thumb_legend = match.group(1)
                            thumb_path = match.group(2)
                            thumb_found = True
                            title_just_found = False
                            if self.poster == 1:
                                i += 1
                                while i < len(lines) and lines[i].strip() == '':
                                    i += 1
                                continue
                        else:
                            temp_thumb_legend = match.group(1)
                            if temp_thumb_legend.endswith(" background"):
                                first_image = False
                            elif temp_thumb_legend.endswith(" thumb"):
                                thumb_legend = temp_thumb_legend.replace(" thumb","")
                                thumb_path = match.group(2)
                                line = line.replace(" thumb","")
                                thumb_found = True
                                if self.poster == 1:
                                    i += 1
                                    continue
                            elif first_image:
                                thumb_legend = temp_thumb_legend
                                thumb_path = match.group(2)
                                thumb_found = True
                                first_image = False
                                if self.poster == 1:
                                    i += 1
                                    continue

                
                # Ajouter la ligne au contenu
                content_lines.append(line)
                i += 1
                if title:
                    title_just_found = False 
                        
            # Construire le contenu final puis convertir en HTML
            content = ''.join(content_lines).strip()
            content = self.strip_comments(content)
            content = self.route_include_to_html(content, frontmatter)
            content = self.normalise_md(content)
            content = self.to_html(content)

            content = self.link_manager(content, path_md, pub_date, post_type)

            if (
                not thumb_path
                and frontmatter
                and frontmatter.get('background')
            ):
                thumb_path = frontmatter['background']
                thumb_legend = title

            # Extraire la description (premier paragraphe non vide)
            description = ""
            for line in content_lines:
                if line.strip():
                    description = self.resume_paragraph(line.strip())
                    break
    
            # Valeurs par défaut
            if thumb_path and not thumb_legend:
                thumb_legend = title
            
            if path_md in ('home.md', 'footer.md') and pub_date == 0:
                pub_date = pub_update

            pub_date_str = tools.format_timestamp_to_paris_time(pub_date)
            pub_update_str = tools.format_timestamp_to_paris_time(pub_update)

            url = self.post_url(path_md, pub_date, post_type)

            if tags:
                tagslist = self.extract_tags(tags)

            github = self.get_github_url(url)

            datelink = self.date_html(pub_date)

            comments = self.comments(path_md)


            r = {
                "source_path": path,
                "pub_date": pub_date,
                "pub_update": pub_update,
                "title": title,
                "tags": tags,
                "thumb_path": thumb_path,
                "thumb_legend": thumb_legend,
                "content": content,
                "description": description,
                "frontmatter": frontmatter,
                "type": post_type,
                "url": url,
                "pub_date_str": pub_date_str,
                "pub_update_str": pub_update_str,
                "path_md": path_md,
                "tagslist": tagslist,
                "github": github,
                "datelink": datelink,
                "comments": comments
            }
            # print(r)
            return r
            
        except Exception as e:
            print(f"Erreur lors de l'extraction de {path}: {e}")
            exit()

    def count_md_files(self, root_dir):
        """Compte rapidement le nombre de fichiers .md dans l'arborescence"""
        count = 0
        for root, dirs, files in os.walk(root_dir):
            # Appliquer les mêmes filtres que db_builder
            dirs[:] = [d for d in dirs if not d.startswith('_i') and d not in self.config['no_export']]
            
            count += sum(1 for file in files if file.endswith('.md'))
        
        return count

    def db_builder(self, root_dir, reset=False):

        if not os.path.isdir(root_dir):
            raise FileNotFoundError(f"Vault directory not found: {root_dir}")

        self.create_tables(reset)

        total = self.count_md_files(root_dir)
        pbar = logs.DualOutput.dual_tqdm(total=total, desc='Markdonw:')
        present_paths = set()

        for root, dirs, files in os.walk(root_dir):
            # Exlude images dirs
            dirs[:] = [d for d in dirs if not d.startswith('_i') and d not in self.config['no_export']]

            for file in files:
                if file.endswith('.md'):
                    md_source_path = os.path.join(root, file)
                    path_md = os.path.relpath(md_source_path, root_dir)
                    present_paths.add(path_md)
                    pub_update = round(os.path.getmtime(md_source_path))

                    existiting_post = self.existing_post(path_md)
                    if existiting_post and pub_update <= existiting_post['pub_update']:
                        continue

                    #print(root,file,root.replace(root_dir,""))
                    post = self.markdown_extract(md_source_path, path_md, pub_update)
                    if post['pub_date'] == 0:
                        # print("post not ready",post['title'],path_md)
                        continue

                    status = self.insert_post(post, existiting_post)
                    self.new_posts += status['new']
                    self.updated_posts += status['update']

                    if status['id'] and "tags" in post:
                        status = self.insert_tag(status['id'], post['tagslist'], post['pub_update'])
                        self.new_tags += status["new"]
                        self.updated_tags += status["updated"]

                pbar.update(1)

        self.delete_missing_posts(present_paths)
        self.sync_config_tags()
        self.conn.execute(
            '''DELETE FROM tags WHERE site = ? AND NOT EXISTS (
                   SELECT 1 FROM connectors WHERE con_tag_id = tags.tag_id
               )''',
            (self.site,)
        )
        self.conn.commit()
        pbar.close()

        print(self.new_posts, "new posts")
        print(self.updated_posts, "updated posts")
        print(self.deleted_posts, "deleted posts")
        print(self.new_tags, "new tags")
        print(self.updated_tags, "updated tags")
