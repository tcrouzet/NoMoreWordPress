# cd /volume1/docker/gemini/content
# find /volume1/docker/gemini/content -type f ! -name ".DS_Store" -printf '"%p": %T@,\n' | sed '$ s/,$//' | awk 'BEGIN {print "{"} {print} END {print "}"}' > state_file.json

import os
import shutil
import tools
import subprocess
import time

class SyncFiles:

    def __init__(self, source_directory, remote_directory):

        if not self.mount_synology_volume():
            return

        self.source_directory = source_directory

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.parent_dir = os.path.dirname(script_dir) + os.sep
        self.temp_dir = os.path.join(self.parent_dir, "_temp")
        
        self.state_file = "gmi_state.json"
        self.previous_state_path = os.path.join(self.temp_dir, self.state_file)
        self.previous_state = tools.load_json(self.previous_state_path)
        self.previous_state = {k: float(v) for k, v in self.previous_state.items()}

        # print(self.previous_state)
        # exit()

        self.current_state = self.get_file_state(source_directory)
        tools.save_json( os.path.join(self.temp_dir,"gmi_current_state.json"), self.current_state)

        # Identifier les fichiers modifiés avec tolérance
        changed_files = [file for file in self.current_state 
            if self.current_state[file] > float(self.previous_state.get(file, 0))]

        # print(changed_files)

        self.transfer_files(changed_files, remote_directory)

        # Save current file state
        sorted_current_state = dict(sorted(self.current_state.items(), key=lambda x: x[0], reverse=True))
        tools.save_json(self.previous_state_path, sorted_current_state)

    def get_file_state(self, directory):
        print(f"Getting file state for {directory}")
        state = {}
        for root, dirs, files in os.walk(directory):

            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                if file.startswith('.') or file == self.state_file:
                    continue
                filepath = os.path.join(root, file)
                state[filepath] = os.path.getmtime(filepath)
        return state

    def transfer_files(self, changed_files, remote_path):
        for filepath in changed_files:
            # Compute the destination path on the mapped drive
            relative_path = os.path.relpath(filepath, start=self.source_directory)
            destination_path = os.path.join(remote_path, relative_path)

            # Ensure the destination directory exists
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)

            # Copy the file
            shutil.copy2(filepath, destination_path)
            self.current_state[filepath] = time.time()
            print(f"Copied {filepath} to {destination_path}")

    def mount_synology_volume(self):
        server_address = "smb://NasZone._smb._tcp.local/docker"
        try:
            subprocess.run(["osascript", "-e", f'mount volume "{server_address}"'], check=True)
            print("Volume Synology monté avec succès.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors du montage du volume Synology: {e}")
            return False

