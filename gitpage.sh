#!/bin/bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v gh >/dev/null
gh auth status

for repo in md blog; do
    if [[ "$repo" == md ]]; then
        export_dir="$HOME/Documents/GitHub/tcrouzet"
        template_dir="$project_dir/templates/md"
    else
        export_dir="$HOME/Documents/GitHub/blog"
        template_dir="$project_dir/templates/minimalist"
    fi

    remote_url="$(git -C "$export_dir" remote get-url origin)"
    if [[ "$remote_url" != "https://github.com/tcrouzet/$repo.git" && "$remote_url" != "git@github.com:tcrouzet/$repo.git" ]]; then
        printf 'Dépôt inattendu : %s\n' "$export_dir" >&2
        exit 1
    fi
    branch="$(git -C "$export_dir" symbolic-ref --short HEAD)"
    domain="$(< "$template_dir/CNAME")"

    cp "$template_dir/CNAME" "$export_dir/CNAME"
    cp "$template_dir/.nojekyll" "$export_dir/.nojekyll"
    git -C "$export_dir" add -- CNAME .nojekyll
    if ! git -C "$export_dir" diff --cached --quiet -- CNAME .nojekyll; then
        git -C "$export_dir" commit --only -m "Restore GitHub Pages domain" -- CNAME .nojekyll
    fi
    git -C "$export_dir" push origin "$branch"

    gh api --method PUT "repos/tcrouzet/$repo/pages" \
        -f "cname=$domain" -f build_type=legacy \
        -f "source[branch]=$branch" -f 'source[path]=/'
    gh api "repos/tcrouzet/$repo/pages" \
        --jq '{status,cname,html_url,source,https_enforced}'
done
