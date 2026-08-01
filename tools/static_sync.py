"""Synchronisation des fichiers statiques d'un vault vers ses exports."""

import hashlib
import os
import shutil


class StaticSync:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def file_hash(path):
        hasher = hashlib.sha256()
        with open(path, 'rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def remove_empty_dirs(path, export_root):
        directory = os.path.dirname(path)
        while directory != export_root:
            try:
                os.rmdir(directory)
            except OSError:
                break
            directory = os.path.dirname(directory)

    def indexed_files(self, root_path):
        files = {}
        if not os.path.isdir(root_path):
            return files
        for root, _, filenames in os.walk(root_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, root_path)
                files[relative_path] = (
                    file_path,
                    self.file_hash(file_path)
                )
        return files

    def source_root(self):
        static_folder = self.config.get('static_folder')
        if not static_folder:
            return None

        vault_root = os.path.abspath(self.config['vault'])
        source_root = os.path.abspath(os.path.join(vault_root, static_folder))
        if os.path.commonpath((vault_root, source_root)) != vault_root:
            raise ValueError(f"static_folder must be inside vault: {static_folder}")
        if not os.path.isdir(source_root):
            raise FileNotFoundError(f"Static folder not found: {source_root}")
        return source_root

    def sync_export(self, export_root, static_folder, source_files):
        target_root = os.path.abspath(os.path.join(export_root, static_folder))
        if os.path.commonpath((export_root, target_root)) != export_root:
            raise ValueError(f"Static target outside export: {static_folder}")

        os.makedirs(target_root, exist_ok=True)
        target_files = self.indexed_files(target_root)
        changed = 0

        for relative_path, (source_path, content_hash) in source_files.items():
            target_path = os.path.abspath(os.path.join(target_root, relative_path))
            if os.path.commonpath((target_root, target_path)) != target_root:
                raise ValueError(f"Static target outside export: {relative_path}")

            target_matches = (
                relative_path in target_files
                and target_files[relative_path][1] == content_hash
            )
            if not target_matches:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(source_path, target_path)
                changed += 1
                print(f"Copied static file: {target_path}")

        for relative_path in set(target_files) - set(source_files):
            target_path = os.path.abspath(os.path.join(target_root, relative_path))
            if (
                os.path.commonpath((target_root, target_path)) == target_root
                and os.path.isfile(target_path)
            ):
                os.remove(target_path)
                self.remove_empty_dirs(target_path, target_root)
                changed += 1
                print(f"Deleted static file: {target_path}")

        return changed

    def run(self):
        source_root = self.source_root()
        if source_root is None:
            return 0

        static_folder = self.config['static_folder']
        files = self.indexed_files(source_root)
        exports = {
            os.path.abspath(template['export'])
            for template in self.config['templates']
        }
        changed = 0
        for export_root in exports:
            os.makedirs(export_root, exist_ok=True)
            changed += self.sync_export(export_root, static_folder, files)

        print(changed, "updated static files")
        return changed
