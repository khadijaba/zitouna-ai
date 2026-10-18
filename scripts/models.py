"""Share the trained models through one Hugging Face model repo (one folder per module, like models/).

Setup (once): pip install huggingface_hub, then in the root .env:
    HF_MODELS_REPO=<user-or-org>/zitouna-models
    HF_TOKEN=hf_...            # https://huggingface.co/settings/tokens ("Read" to pull, "Write" to push)

Usage:
    python scripts/models.py list                  # folders available on the Hub, with their size
    python scripts/models.py pull                  # download every model into models/
    python scripts/models.py pull m5_ensemble      # download only these folders
    python scripts/models.py push m5_ensemble      # upload models/m5_ensemble (module owner, after retraining)

Then restart the service (docker compose restart m5-assistant): /health shows "modelLoaded": true.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
KEEP_LOCAL = ["README.md", ".gitattributes"]  # never overwrite models/README.md with the Hub's files


def load_env() -> None:
    """Read HF_* variables from the root .env (the environment wins)."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip().startswith("HF_") and value.strip():
            os.environ.setdefault(key.strip(), value.strip())


def settings() -> tuple[str, str | None]:
    load_env()
    repo = os.environ.get("HF_MODELS_REPO")
    if not repo:
        sys.exit("Set HF_MODELS_REPO in .env (e.g. HF_MODELS_REPO=my-user/zitouna-models).")
    return repo, os.environ.get("HF_TOKEN")


def sizes(api, repo: str) -> dict[str, int]:
    """Top-level folder -> total size in bytes."""
    total: dict[str, int] = {}
    for entry in api.list_repo_tree(repo, recursive=True):
        if "/" in entry.path and getattr(entry, "size", None):
            folder = entry.path.split("/", 1)[0]
            total[folder] = total.get(folder, 0) + entry.size
    return total


def cmd_list(api, repo: str, _args) -> None:
    found = sizes(api, repo)
    if not found:
        print(f"No model in {repo} yet. Upload one with: python scripts/models.py push <folder>")
    for folder, size in sorted(found.items()):
        local = "downloaded" if (MODELS / folder).exists() else "not downloaded"
        print(f"{folder:<20} {size / 1e6:8.1f} MB   {local}")


def cmd_pull(api, repo: str, args) -> None:
    from huggingface_hub import snapshot_download

    available = sizes(api, repo)
    wanted = args.folders or sorted(available)
    missing = [f for f in wanted if f not in available]
    if missing:
        sys.exit(f"Not on the Hub: {', '.join(missing)}. Available: {', '.join(sorted(available)) or 'none'}")
    print(f"Downloading {', '.join(wanted)} from {repo} into models/ ...")
    snapshot_download(repo, local_dir=MODELS, token=api.token,
                      allow_patterns=[f"{f}/*" for f in wanted], ignore_patterns=KEEP_LOCAL)  # fmt: skip
    print("Done. Restart the AI services: docker compose restart")


def cmd_push(api, repo: str, args) -> None:
    folder = MODELS / args.folder
    if not folder.is_dir():
        sys.exit(f"models/{args.folder} does not exist.")
    api.create_repo(repo, repo_type="model", private=True, exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT)
    message = f"{args.folder}: upload (code at {commit.stdout.strip() or 'unknown commit'})"
    print(f"Uploading models/{args.folder} to {repo}/{args.folder} ...")
    api.upload_folder(repo_id=repo, folder_path=folder, path_in_repo=args.folder, commit_message=message,
                      ignore_patterns=["__pycache__/*", ".cache/*"])  # fmt: skip
    print(f"Done: https://huggingface.co/{repo}/tree/main/{args.folder}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="folders available on the Hub")
    pull = sub.add_parser("pull", help="download models into models/")
    pull.add_argument("folders", nargs="*", help="e.g. m5_ensemble (default: all)")
    push = sub.add_parser("push", help="upload one folder of models/")
    push.add_argument("folder", help="e.g. m5_ensemble")
    args = parser.parse_args()

    try:
        from huggingface_hub import HfApi
        from huggingface_hub.errors import HfHubHTTPError, RepositoryNotFoundError
    except ImportError:
        sys.exit("Missing library: pip install huggingface_hub")
    repo, token = settings()
    api = HfApi(token=token)
    try:
        {"list": cmd_list, "pull": cmd_pull, "push": cmd_push}[args.command](api, repo, args)
    except RepositoryNotFoundError:
        sys.exit(f"{repo} not found, or no access: check HF_MODELS_REPO and HF_TOKEN in .env "
                 "(a private repo needs a token of a member).")  # fmt: skip
    except HfHubHTTPError as e:
        sys.exit(f"Hugging Face error: {e}")


if __name__ == "__main__":
    main()
