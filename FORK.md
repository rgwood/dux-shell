# Reilly's fork

## Remotes and branches

- `origin` is upstream (`duxlabs-dev/dux-shell`). `fork` is mine (`rgwood/dux-shell`).
- `reilly.wood/local` is the patch stack I actually run: one commit per patch on
  top of the release tag that matches the installed `dms` package
  (`dpkg-query -W dms`). The Go `dms` binary comes from the PPA, so the QML must
  match its version. Never base this branch on `master`.
- Patches meant for upstream get their own `reilly.wood/<name>` branch off
  `origin/master`, and get cherry-picked onto `reilly.wood/local` to use them now.
- This file, `CLAUDE.md` and the pointer at the top of `AGENTS.md` live only on
  `reilly.wood/local`, in their own commit. Keep them out of upstream branches.
- When upstream merges one of my patches and the PPA ships it, drop that commit
  from `reilly.wood/local` during the next rebase.

## Deploying

DMS runs from `~/source/dux-shell-deploy/quickshell`, a detached worktree of
`reilly.wood/local`. `DMS_SHELL_DIR` points there through a `dms.service` drop-in
from my dotfiles (`~/dotfiles/linux/systemd/dms-shell-dir.conf`).

- Never edit the deploy worktree by hand. Commit here, then run `dms-deploy`
  (from `~/dotfiles/bin/dms-deploy`), which updates the worktree and restarts
  `dms.service`. `dms-deploy --no-restart` skips the restart.
- Restarting DMS is visible to me (the bar and dock blink), so ask before
  deploying.
- Logs: `journalctl --user -u dms.service` or
  `qs log -p ~/source/dux-shell-deploy/quickshell`.

## Syncing with a new release

`dms-deploy` refuses to deploy when the PPA version and the branch's base tag
differ, and prints the rebase command. The rebase looks like this:

```bash
git fetch origin --tags
git rebase --onto v2.1.3 v2.1.2 reilly.wood/local
```

Then run `dms-deploy`.
