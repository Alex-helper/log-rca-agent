"""Force-publish local commit history to GitHub via gh api (git HTTPS blocked)."""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "Alex-helper"
REPO = "log-rca-agent"
BLOB_CACHE: dict[str, str] = {}


def run(cmd: list[str]) -> bytes:
    return subprocess.check_output(cmd, cwd=ROOT)


def gh_api(method: str, path: str, payload: dict | None = None) -> dict:
    args = ["gh", "api", "-X", method, path]
    tmp = None
    if payload is not None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump(payload, f, ensure_ascii=False)
            tmp = f.name
        args.extend(["--input", tmp])
    try:
        for attempt in range(10):
            try:
                out = subprocess.check_output(args, cwd=ROOT, stderr=subprocess.STDOUT)
                return json.loads(out.decode() or "{}")
            except subprocess.CalledProcessError as e:
                err = e.output.decode("utf-8", "ignore") if e.output else str(e)
                retryable = (
                    "500",
                    "502",
                    "503",
                    "timeout",
                    "EOF",
                    "reset",
                    "connection",
                    "TLS",
                    "wsarecv",
                )
                if attempt < 9 and any(x.lower() in err.lower() for x in retryable):
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise RuntimeError(err) from e
    finally:
        if tmp:
            Path(tmp).unlink(missing_ok=True)
    return {}


def blob_for(path: str, data: bytes) -> str:
    key = hashlib.sha256(data).hexdigest()
    if key in BLOB_CACHE:
        return BLOB_CACHE[key]
    # Prefer utf-8 text when possible
    try:
        text = data.decode("utf-8")
        if "\x00" not in text:
            sha = gh_api(
                "POST",
                f"repos/{OWNER}/{REPO}/git/blobs",
                {"content": text, "encoding": "utf-8"},
            )["sha"]
            BLOB_CACHE[key] = sha
            return sha
    except UnicodeDecodeError:
        pass
    b64 = base64.b64encode(data).decode("ascii")
    sha = gh_api(
        "POST",
        f"repos/{OWNER}/{REPO}/git/blobs",
        {"content": b64, "encoding": "base64"},
    )["sha"]
    BLOB_CACHE[key] = sha
    return sha


def main() -> None:
    commits = run(["git", "rev-list", "--reverse", "main"]).decode().split()
    print(f"commits={len(commits)}")
    parent = None
    tip = None

    for idx, commit in enumerate(commits, 1):
        msg = run(["git", "log", "-1", "--format=%B", commit]).decode("utf-8").rstrip() + "\n"
        # -z + quotepath=false avoids octal-escaped Chinese filenames on Windows
        raw_names = run(
            ["git", "-c", "core.quotepath=false", "ls-tree", "-r", "-z", "--name-only", commit]
        )
        names = [n.decode("utf-8") for n in raw_names.split(b"\0") if n]
        tree_items = []
        for i, rel in enumerate(names, 1):
            data = run(["git", "-c", "core.quotepath=false", "show", f"{commit}:{rel}"])
            sha = blob_for(rel, data)
            tree_items.append(
                {"path": rel.replace("\\", "/"), "mode": "100644", "type": "blob", "sha": sha}
            )
            if i % 20 == 0:
                print(f"  [{idx}] blob {i}/{len(names)}")
        tree = gh_api("POST", f"repos/{OWNER}/{REPO}/git/trees", {"tree": tree_items})
        payload = {"message": msg, "tree": tree["sha"], "parents": [parent] if parent else []}
        created = gh_api("POST", f"repos/{OWNER}/{REPO}/git/commits", payload)
        parent = created["sha"]
        tip = parent
        subject = msg.splitlines()[0]
        print(f"[{idx}/{len(commits)}] {tip[:7]} {subject}")

    assert tip
    try:
        gh_api(
            "PATCH",
            f"repos/{OWNER}/{REPO}/git/refs/heads/main",
            {"sha": tip, "force": True},
        )
    except RuntimeError:
        gh_api(
            "POST",
            f"repos/{OWNER}/{REPO}/git/refs",
            {"ref": "refs/heads/main", "sha": tip},
        )
    print("FORCE_PUSH_OK", tip)
    print(f"https://github.com/{OWNER}/{REPO}/commits/main")


if __name__ == "__main__":
    main()
