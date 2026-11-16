import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import sync_files, tools


class SyncFilesTests(unittest.TestCase):
    def test_machine_move_preserves_state_and_only_copies_changes(self):
        for legacy_root in ('/Users/ancien/Documents/gemini', None):
            with self.subTest(legacy_root=legacy_root), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                source = project / 'gemini'
                remote = project / 'remote'
                cache = project / '_temp'
                cache.mkdir()
                (source / '2026/11/i').mkdir(parents=True)
                contents = {'2026/11/i/photo.jpg': b'image existante', '2026/11/post.gmi': b'texte existant'}
                state = {}
                for relative, content in contents.items():
                    path = source / relative
                    path.write_bytes(content)
                    os.utime(path, (100, 100))
                    key = f'{legacy_root}/{relative}' if legacy_root else relative
                    state[key] = 100
                state_path = cache / 'gmi_state.json'
                state_path.write_text(json.dumps(state))

                with patch.object(sync_files, 'tools', tools), patch.object(sync_files, '__file__', str(project / 'tools/sync_files.py')), patch.object(sync_files.SyncFiles, 'mount_synology_volume', return_value=True):
                    sync_files.SyncFiles(str(source), str(remote))
                    self.assertFalse(remote.exists(), 'Les fichiers inchangés ne doivent pas être recopiés')
                    self.assertEqual(json.loads(state_path.read_text()), {path: 100 for path in contents})

                    (source / '2026/11/post.gmi').write_bytes(b'texte actualise')
                    (source / 'nouveau.gmi').write_bytes(b'nouveau texte')
                    sync_files.SyncFiles(str(source), str(remote))
                    self.assertEqual((remote / '2026/11/post.gmi').read_bytes(), b'texte actualise')
                    self.assertEqual((remote / 'nouveau.gmi').read_bytes(), b'nouveau texte')
                    self.assertFalse((remote / '2026/11/i/photo.jpg').exists())
                    saved_state = json.loads(state_path.read_text())
                    self.assertTrue(all(not os.path.isabs(path) for path in saved_state))
                    sync_files.SyncFiles(str(source), str(remote))
                    self.assertEqual(json.loads(state_path.read_text()), saved_state)


if __name__ == '__main__':
    unittest.main()
