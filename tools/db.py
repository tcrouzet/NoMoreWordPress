import sqlite3
import os
import re
import json
import datetime

class Db:

    def __init__(self, config):
        self.config = config

        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir) + os.sep
        script_dir = parent_dir

        temp_dir = os.path.join(script_dir, "_temp")
        os.makedirs(temp_dir, exist_ok=True)

        self.db = os.path.join(temp_dir, "posts.db")
        self.conn = sqlite3.connect(self.db)
        self.conn.row_factory = sqlite3.Row

        self.new_posts = 0
        self.updated_posts = 0
        self.used_tags = set()
        self.used_years = set()

    def create_table_posts(self, reset=False):
        c = self.conn.cursor()

        if reset:
            print("Reset table posts")
            c.execute('DROP TABLE IF EXISTS posts')

        c.execute(f'''CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    path_md TEXT UNIQUE,
                    pub_date INTEGER,
                    pub_update INTEGER,
                    thumb_path TEXT DEFAULT '',
                    thumb_legend TEXT DEFAULT '',
                    type INTEGER CHECK(type IN (0, 1)),  -- 0 pour post, 1 pour page
                    tags TEXT DEFAULT '[]',
                    updated BOOLEAN DEFAULT TRUE
                );''')
        self.conn.commit()

    def insert_post(self, post):

        if 'tags' in post and isinstance(post['tags'], list):
            tags_set = set(post['tags'])
            post['tags'] = json.dumps(post['tags'])

        #print(post)
        #exit()

        c = self.conn.cursor()
        c.execute('SELECT * FROM posts WHERE path_md = :path_md', {'path_md': post['path_md']})
        existing_post = c.fetchone()

        if existing_post and post['pub_update'] > existing_post['pub_update']:
            # Update post

            query = '''UPDATE posts SET
                        title = :title,
                        pub_date = :pub_date,
                        pub_update = :pub_update,
                        thumb_path = :thumb_path,
                        thumb_legend = :thumb_legend,
                        type = :type,
                        tags = :tags,
                        updated = TRUE
                    WHERE path_md = :path_md;'''
            c.execute(query, post)

            # existing_tags_set = set(json.loads(existing_post['tags']))
            # self.used_tags.update( existing_tags_set - tags_set )
            self.used_tags.update( tags_set )

            return 0, 1

        else:
            # New post

            query = '''INSERT OR IGNORE INTO posts 
                    (title, path_md, pub_date, pub_update, thumb_path, thumb_legend, type, tags)
                    VALUES (:title, :path_md, :pub_date, :pub_update, :thumb_path, :thumb_legend, :type, :tags);             
                    '''
            c.execute(query, post)
            if c.rowcount > 0:
                self.used_tags.update( tags_set )
                date_time = datetime.datetime.fromtimestamp(post['pub_date'])
                self.used_years.add( date_time.year )
                return 1, 0
            else:
                return 0, 0

    def insert_post_old(self, post):

        if 'tags' in post and isinstance(post['tags'], list):
            post['tags'] = json.dumps(post['tags'])

        #print(post)
        #exit()

        query = '''INSERT OR IGNORE INTO posts 
                (title, path_md, pub_date, pub_update, thumb_path, thumb_legend, type, tags)
                VALUES (:title, :path_md, :pub_date, :pub_update, :thumb_path, :thumb_legend, :type, :tags)
                ON CONFLICT(path_md) DO UPDATE SET
                        title = excluded.title,
                        pub_date = excluded.pub_date,
                        pub_update = excluded.pub_update,
                        thumb_path = excluded.thumb_path,
                        thumb_legend = excluded.thumb_legend,
                        type = excluded.type,
                        tags = excluded.tags,
                        updated = TRUE
                    WHERE excluded.pub_update > pub_update;             
                '''
        c = self.conn.cursor()
        c.execute(query, post)
        if c.rowcount > 0:
            return True
        else:
            return False

    def updated(self, post):

        query = '''UPDATE posts SET updated = False WHERE id = ?;'''
        c = self.conn.cursor()

        c.execute(query, (post['id'],))
        if c.rowcount > 0:
            return True
        else:
            return False

    def delete_post(self, post):
        c = self.conn.cursor()

        query = '''DELETE FROM posts WHERE id = ?;'''
        c.execute(query, (post['id'],))
        if c.rowcount > 0:
            return True
        else:
            return False

    def db_commit(self):
        self.conn.commit()

    def get_row_factory(self):
        return self.conn.row_factory

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

    def markdown_extract(self, path):
        creation_time = 0
        modification_time = round(os.path.getmtime(path))

        # Read the file and extract title and tags
        title = None
        tags = []
        thumb_path = None
        thumb_legend = None
        with open(path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in lines:
                # Find title
                if line.startswith('# ') and not title:
                    title = line.strip('# ')
                    title = title.strip()
                # Check tags
                if line.startswith('#') and ' ' in line:
                    potential_tags = line.strip().split()
                    if all(tag.startswith('#') for tag in potential_tags):
                        tags = [tag[1:] for tag in potential_tags if tag.startswith('#')]
                        tags, creation_time = self.filter_tags(tags)
                #Thumb
                if '![' in line and thumb_path is None:
                    match = re.search(r'!\[(.*?)\]\((.*?)\)', line)
                    if match:
                        thumb_legend = match.group(1)
                        thumb_path = match.group(2)

            if thumb_path and not thumb_legend:
                thumb_legend = title
            answer = {"pub_date":creation_time, "pub_update":modification_time, "title":title, "tags":tags, "thumb_legend":thumb_legend, "thumb_path":thumb_path}
            return answer
            
        return None


    def db_builder(self, root_dir,reset=False):

        self.create_table_posts(reset)
        count_added = 0
        count_updated = 0

        for root, dirs, files in os.walk(root_dir):
            # Exlude images dirs
            # dirs[:] = [d for d in dirs if not d.startswith('_i')]
            dirs[:] = [d for d in dirs if not d.startswith('_i') and d not in self.config['no_export']]

            for file in files:
                if file.endswith('.md'):
                    md_path = os.path.join(root, file)
                    #print(root,file,root.replace(root_dir,""))
                    post = self.markdown_extract(md_path)
                    if post['pub_date'] == 0:
                        print("post not ready",post['title'],md_path)
                        continue

                    post['path_md'] = os.path.join(root.replace(root_dir,"").strip("/"), file)

                    if any(post['path_md'].startswith(prefix) for prefix in self.config['pages']):
                        post['type'] = 1
                    else:
                        post['type'] = 0

                    #test_insert_post(post)
                    #print(post)

                    added, updated = self.insert_post(post)
                    self.new_posts += added
                    self.updated_posts += updated

        self.conn.commit()


    def get_posts(self, condition=None):
        c = self.conn.cursor()

        if condition:
            where = f"WHERE {condition}"
        else:
            where = ""
        query = f"SELECT * FROM posts {where} ORDER BY pub_date DESC"
        c.execute(query)
        return c.fetchall()

    def get_posts_updated(self):
        return self.get_posts("updated=1")

    def get_all_posts(self):
        return self.get_posts("type=0")

    def get_blog_posts(self, tags_tuple):
        if isinstance(tags_tuple,tuple):
            plus = str(tags_tuple)
        else:
            plus = "('{tags_tuple}')"
        where = f"id NOT IN (SELECT posts.id FROM posts JOIN json_each(posts.tags) ON json_each.value IN {plus}) AND type=0"
        return self.get_posts(where)

    def get_posts_by_year(self, year, exclude_tags=None):
        where = f"strftime('%Y', datetime(pub_date, 'unixepoch')) = '{year}' AND type=0 "
        if exclude_tags:
             where += "AND id NOT IN (SELECT posts.id FROM posts JOIN json_each(posts.tags) ON json_each.value IN " + str(exclude_tags) + ")"
        return self.get_posts(where)
    
    def get_years(self):
        c = self.conn.cursor()

        query = '''
        SELECT DISTINCT strftime('%Y', datetime(pub_date, 'unixepoch')) AS year
        FROM posts WHERE type = 0
        ORDER BY year DESC
        '''
        c.execute(query)
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
        WHERE path_md = ? LIMIT 1
        '''
        c.execute(query, (path,))
        post = c.fetchone()
        return post


    def get_posts_by_tag(self, tag, limit=""):
        if not tag:
            return None
        c = self.conn.cursor()

        if limit:
            limit = f"LIMIT {limit}"
        
        query = f'''
        SELECT * FROM posts, json_each(posts.tags)
        WHERE json_each.value = ?
        ORDER BY pub_date DESC {limit}
        '''
        c.execute(query, (tag,))
        posts = c.fetchall()
        return posts

    def get_tags(self, order="t.count DESC", exclude_tags=None):
        c = self.conn.cursor()

        where_clause = ""
        if exclude_tags:
            tags_list = ','.join('?' for _ in exclude_tags)  # Créer une chaîne de placeholders
            where_clause = f"AND t.tag NOT IN ({tags_list})"
        
        query = f'''
        SELECT t.tag,
            t.count,
            '/tag/' || t.tag as path_md,
            5 as type,
            p.id,
            p.path_md as post_md,
            p.thumb_path,
            p.thumb_legend, 
            p.pub_update
            FROM (
                SELECT json_each.value AS tag, 
                    COUNT(*) AS count, 
                    MAX(posts.pub_date) AS most_recent_date
                FROM posts
                JOIN json_each(posts.tags)
                GROUP BY json_each.value
            ) AS t
            JOIN posts AS p ON p.pub_date = t.most_recent_date
            WHERE EXISTS (
                SELECT 1 FROM json_each(p.tags)
                WHERE json_each.value = t.tag
            ) {where_clause}
            ORDER BY {order}
        '''

        if exclude_tags:
            c.execute(query, exclude_tags)
        else:
            c.execute(query)
        tags = c.fetchall()
        
        return tags

    def get_last_published_post(self):
        c = self.conn.cursor()
        query = '''
        SELECT * FROM posts
        ORDER BY pub_date DESC
        LIMIT 1
        '''
        c.execute(query)
        post = c.fetchone()
        return post

    def timestamp_to_date(self, timestamp):
        date_time = datetime.datetime.fromtimestamp(timestamp)
        readable_date = date_time.strftime("%Y-%m-%d")
        return readable_date

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

    def test_insert_post(self, post=None):
        self.create_table_posts(True)
        if not post:
            post = {
                'title': 'Test Entry', 
                'path_md': 'test/path.md', 
                'pub_date': 1379706780, 
                'pub_update': 1416085181, 
                'thumb_path': '_i/test.jpg', 
                'thumb_legend': 'Test Image', 
                'type': 1, 
                'tags': json.dumps(["test"])
            }
        result = self.insert_post(post)
        self.conn.commit()
        print("Insert/Update result:", result)
        self.list_posts()
