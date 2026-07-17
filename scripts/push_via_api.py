"""Push current git-tracked files to GitHub via Git Data API (when git HTTPS is blocked)."""
from __future__ import annotations

import base64
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "Alex-helper"
REPO = "log-rca-agent"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
API = "https://api.github.com"


def api(method: str, path: str, data: dict | None = None) -> dict:
    url = API + path
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read()
            return json.loads(raw.decode()) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"{method} {path} -> {e.code}: {err}") from e


def main() -> None:
    if not TOKEN:
        raise SystemExit("GH_TOKEN missing")

    out = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    files = [f.decode("utf-8") for f in out.split(b"\0") if f]
    print(f"files={len(files)}")

    tree: list[dict] = []
    for i, rel in enumerate(files, 1):
        p = ROOT / rel
        if not p.is_file():
            continue
        content = p.read_bytes()
        if len(content) > 80 * 1024 * 1024:
            print("skip large", rel)
            continue
        # executable bit for scripts rarely needed on Windows bats
        mode = "100755" if rel.endswith(".sh") else "100644"
        blob = api(
            "POST",
            f"/repos/{OWNER}/{REPO}/git/blobs",
            {
                "content": base64.b64encode(content).decode("ascii"),
                "encoding": "base64",
            },
        )
        tree.append(
            {
                "path": rel.replace("\\", "/"),
                "mode": mode,
                "type": "blob",
                "sha": blob["sha"],
            }
        )
        if i % 10 == 0 or i == len(files):
            print(f"blob {i}/{len(files)}")

    print("creating tree...")
    tree_obj = api("POST", f"/repos/{OWNER}/{REPO}/git/trees", {"tree": tree})
    print("tree", tree_obj["sha"])

    commit = api(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/commits",
        {
            "message": "feat: log RCA agent MVP with MCP ReAct and free demo\n",
            "tree": tree_obj["sha"],
            "parents": [],
        },
    )
    print("commit", commit["sha"])

    try:
        api(
            "POST",
            f"/repos/{OWNER}/{REPO}/git/refs",
            {"ref": "refs/heads/main", "sha": commit["sha"]},
        )
        print("ref created")
    except RuntimeError as e:
        print("create ref failed, force update:", e)
        api(
            "PATCH",
            f"/repos/{OWNER}/{REPO}/git/refs/heads/main",
            {"sha": commit["sha"], "force": True},
        )
        print("ref updated")

    # ensure default branch
    try:
        api("PATCH", f"/repos/{OWNER}/{REPO}", {"default_branch": "main"})
    except RuntimeError as e:
        print("default_branch warn:", e)

    info = api("GET", f"/repos/{OWNER}/{REPO}")
    print("URL", info.get("html_url"))
    print("default_branch", info.get("default_branch"))
    print("PUSH_OK")


if __name__ == "__main__":
    main()
