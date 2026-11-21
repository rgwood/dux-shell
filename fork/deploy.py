#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Deploy this fork's patched DMS QML (see FORK.md).

Checks that reilly.wood/local sits on the release tag matching the installed
`dms` package, moves the deploy worktree to the branch tip, makes sure
dms.service runs from it, and restarts dms.service.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

BRANCH = "reilly.wood/local"
SUBMODULE = "dux-qml-common"  # quickshell/DCommon symlinks into it
SERVICE = "dms.service"
DROP_IN = Path.home() / ".config/systemd/user/dms.service.d/shell-dir.conf"


def git(*args: str, cwd: Path, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def main_repo() -> Path:
    # Works whether this runs from the main clone or the deploy worktree.
    here = Path(__file__).resolve().parent
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=here)
    return Path(common).parent


def installed_tag() -> str:
    version = subprocess.run(
        ["dpkg-query", "-W", "-f=${Version}", "dms"], capture_output=True, text=True, check=True
    ).stdout
    match = re.match(r"(\d+\.\d+\.\d+)", version)
    if not match:
        sys.exit(f"Can't parse installed dms version: {version!r}")
    return f"v{match.group(1)}"


def check_base(repo: Path, tag: str) -> None:
    tag_ref = ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"]
    if subprocess.run(tag_ref, cwd=repo, capture_output=True).returncode:
        print(f"Fetching tags (don't have {tag} yet)...")
        git("fetch", "origin", "--tags", "--quiet", cwd=repo)
    base = git("describe", "--tags", "--abbrev=0", "--match", "v*", BRANCH, cwd=repo)
    if base != tag:
        sys.exit(
            f"{BRANCH} is based on {base}, but the installed dms package is {tag}.\n"
            f"Rebase the patch stack first:\n"
            f"  git -C {repo} fetch origin --tags\n"
            f"  git -C {repo} rebase --onto {tag} {base} {BRANCH}"
        )


def update_worktree(repo: Path, deploy: Path) -> None:
    if not deploy.exists():
        print(f"Creating deploy worktree at {deploy}")
        git("worktree", "add", "--quiet", "--detach", str(deploy), BRANCH, cwd=repo)
    elif git("status", "--porcelain", cwd=deploy):
        sys.exit(f"{deploy} has local changes; make them in {repo} instead.")
    git("checkout", "--quiet", "--detach", BRANCH, cwd=deploy)
    git("submodule", "update", "--init", "--quiet", SUBMODULE, cwd=deploy)


def ensure_drop_in(deploy: Path) -> None:
    content = (
        "# Written by fork/deploy.py in ~/source/dux-shell (reilly.wood/local).\n"
        "# Runs DMS's QML from the fork's deploy worktree instead of the package.\n"
        "[Service]\n"
        f"Environment=DMS_SHELL_DIR={deploy / 'quickshell'}\n"
    )
    if DROP_IN.is_file() and not DROP_IN.is_symlink() and DROP_IN.read_text() == content:
        return
    DROP_IN.parent.mkdir(parents=True, exist_ok=True)
    DROP_IN.unlink(missing_ok=True)
    DROP_IN.write_text(content)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    print(f"Wrote {DROP_IN}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-restart", action="store_true", help=f"don't restart {SERVICE}")
    args = parser.parse_args()

    repo = main_repo()
    deploy = repo.parent / f"{repo.name}-deploy"
    tag = installed_tag()
    check_base(repo, tag)
    update_worktree(repo, deploy)
    ensure_drop_in(deploy)

    head = git("log", "-1", "--format=%h %s", cwd=deploy)
    patches = git("log", "--format=%h %s", f"{tag}..{BRANCH}", cwd=repo).splitlines()
    print(f"Deployed {head}\nPatches on {tag}:")
    print("\n".join(f"  {line}" for line in patches) or "  (none)")

    if not args.no_restart:
        subprocess.run(["systemctl", "--user", "restart", SERVICE], check=True)
        print(f"Restarted {SERVICE}")


if __name__ == "__main__":
    main()
