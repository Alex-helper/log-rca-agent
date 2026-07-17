"""Push tracked files using `gh api` (more reliable than raw urllib on some networks)."""
from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "Alex-helper"
REPO = "log-rca-agent"


def gh_api(method: str, path: str, payload: dict | None = None) -> dict:
    args = ["gh", "api", "-X", method, path]
    if payload is not None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump(payload, f, ensure_ascii=False)
            tmp = f.name
        args.extend(["--input", tmp])
    for attempt in range(5):
        try:
            out = subprocess.check_output(args, cwd=ROOT, stderr=subprocess.STDOUT)
            if payload is not None:
                Path(tmp).unlink(missing_ok=True)
            return json.loads(out.decode() or "{}")
        except subprocess.CalledProcessError as e:
            err = e.output.decode("utf-8", "ignore") if e.output else str(e)
            if attempt < 4 and ("500" in err or "502" in err or "503" in err):
                time.sleep(1.5 * (attempt + 1))
                continue
            if payload is not None:
                Path(tmp).unlink(missing_ok=True)
            raise RuntimeError(err) from e
    return {}


def main() -> None:
    out = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    files = [f.decode("utf-8") for f in out.split(b"\0") if f]
    print(f"files={len(files)}")

    tree: list[dict] = []
    for i, rel in enumerate(files, 1):
        p = ROOT / rel
        if not p.is_file():
            continue
        content = p.read_text(encoding="utf-8", errors="surrogateescape")
        # Prefer UTF-8 text; for binary fall back to base64 via bytes hex path
        try:
            text = p.read_text(encoding="utf-8")
            blob = gh_api(
                "POST",
                f"repos/{OWNER}/{REPO}/git/blobs",
                {"content": text, "encoding": "utf-8"},
            )
        except Exception:
            import base64

            b64 = base64.b64encode(p.read_bytes()).decode("ascii")
            blob = gh_api(
                "POST",
                f"repos/{OWNER}/{REPO}/git/blobs",
                {"content": b64, "encoding": "base64"},
            )
        tree.append(
            {
                "path": rel.replace("\\", "/"),
                "mode": "100644",
                "type": "blob",
                "sha": blob["sha"],
            }
        )
        if i % 5 == 0 or i == len(files):
            print(f"blob {i}/{len(files)} {rel}")

    print("creating tree...")
    tree_obj = gh_api("POST", f"repos/{OWNER}/{REPO}/git/trees", {"tree": tree})
    print("tree", tree_obj["sha"])

    commit = gh_api(
        "POST",
        f"repos/{OWNER}/{REPO}/git/commits",
        {
            "message": "feat: log RCA agent MVP with MCP ReAct and free demo",
            "tree": tree_obj["sha"],
            "parents": [],
        },
    )
    print("commit", commit["sha"])

    try:
        gh_api(
            "POST",
            f"repos/{OWNER}/{REPO}/git/refs",
            {"ref": "refs/heads/main", "sha": commit["sha"]},
        )
        print("ref created")
    except RuntimeError as e:
        print("create ref failed, updating:", str(e)[:200])
        gh_api(
            "PATCH",
            f"repos/{OWNER}/{REPO}/git/refs/heads/main",
            {"sha": commit["sha"], "force": True},
        )
        print("ref updated")

    gh_api("PATCH", f"repos/{OWNER}/{REPO}", {"default_branch": "main"})
    info = gh_api("GET", f"repos/{OWNER}/{REPO}")
    print("URL", info.get("html_url"))
    print("PUSH_OK")


if __name__ == "__main__":
    main()
