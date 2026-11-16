import ast
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from tools import tools


class PagesAssetsTests(unittest.TestCase):
    def test_markdown_sync_restores_pages_files(self):
        script = Path(__file__).resolve().parents[1] / 'tools/sync_md.py'
        tree = ast.parse(script.read_text())
        selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ('index', 'clean_files')]
        selected += [node for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'preserved_files' for target in node.targets)]
        with tempfile.TemporaryDirectory() as directory:
            export = Path(directory) / 'export'
            export.mkdir()
            namespace = {'__file__': str(script), 'os': os, 'shutil': shutil, 'tools': tools, 'config': {'export_github_md': str(export)}}
            exec(compile(ast.Module(body=selected, type_ignores=[]), str(script), 'exec'), namespace)
            namespace['index']()
            self.assertEqual((export / 'CNAME').read_text().strip(), 'md.tcrouzet.com')
            self.assertTrue((export / '.nojekyll').is_file())
            namespace['clean_files'](str(Path(directory) / 'vault'), str(export), namespace['preserved_files'])
            self.assertTrue((export / 'CNAME').is_file())
            self.assertTrue((export / '.nojekyll').is_file())
            namespace['index']()
            self.assertTrue((export / 'index.html').is_file())


if __name__ == '__main__':
    unittest.main()
