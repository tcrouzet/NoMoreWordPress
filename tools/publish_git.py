"""Commit et pousse les dossiers d'export Git configurés pour un site."""

import os
import subprocess
import sys
from datetime import datetime

import tools


def publish_export(export_dir):
    export_dir = os.path.abspath(export_dir)
    if not os.path.isdir(os.path.join(export_dir, ".git")):
        raise FileNotFoundError(f"Dossier Git introuvable : {export_dir}")

    subprocess.run(["git", "add", "-A"], cwd=export_dir, check=True)
    diff_command = ["git", "diff", "--cached", "--quiet"]
    diff_status = subprocess.run(diff_command, cwd=export_dir).returncode
    if diff_status not in (0, 1):
        raise subprocess.CalledProcessError(diff_status, diff_command)
    if diff_status == 0:
        print(f"GitHub : aucun changement à publier depuis {export_dir}")
        return False

    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subprocess.run(
        ["git", "commit", "-m", f"sync {current_date}"],
        cwd=export_dir,
        check=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "HEAD"],
        cwd=export_dir,
        check=True,
    )
    return True


def publish_site(config):
    published = 0
    for template in config.get("templates", []):
        if template.get("skip", False):
            continue
        github_sync = any(
            sync.get("name") == "github"
            for sync in template.get("sync", [])
        )
        if github_sync and publish_export(template["export"]):
            published += 1
    return published


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        raise SystemExit("Usage: python3 tools/publish_git.py nom_du_site")

    site = sys.argv[1].strip()
    publish_site(tools.site_yml(site))


if __name__ == "__main__":
    main()
