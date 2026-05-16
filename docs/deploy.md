# EC-CUBE FIM — Deploy Guide

> Replace `/var/www/html` in all examples below with the `root_path` value
> from `/etc/eccube-fim/daemon.yaml`.

## Security model

The installer runs `secure_git_dir`, which sets:

```
chown -R root:root /var/www/html/.git
chmod -R go-rwx    /var/www/html/.git
```

This prevents the web user (`apache` / `www-data`) from reading or writing
`.git`. An attacker who compromises the PHP process cannot alter git history
to hide a tampered file. The FIM daemon (running as root) can still run
`git diff` to detect changes.

Source files (`.php`, `.twig`, etc.) remain `root:root 644` after every pull.
Apache can read them but cannot modify them — this is intentional.

## How to deploy (git pull)

Because `.git` is root-only, all `git pull` commands must run as root:

```bash
sudo git -c "safe.directory=/var/www/html" -C /var/www/html pull
```

Or via a deploy user with sudo access:

```bash
sudo sh -c 'git -c "safe.directory=/var/www/html" -C /var/www/html pull'
```

Do **not** run `git pull` as `apache` or any other non-root user — it will
fail with `Permission denied` on `.git`.

## What happens after git pull

The installer places a post-merge hook at `.git/hooks/post-merge` (owned by
root, mode 700). After every successful `git pull`, the hook automatically
restores web-user ownership on the EC-CUBE writable directories:

| Directory | Purpose |
|-----------|---------|
| `var/` | cache, logs, sessions — written by PHP |
| `html/upload/` | user file uploads |
| `app/Plugin/` | installed plugin code |
| `app/PluginData/` | plugin runtime data |

The hook only chowns directories that already exist, so it is safe to run
against any EC-CUBE version.

## If you add a new writable directory

If a customisation introduces a directory that PHP must write to (e.g.
`var/myplugin/`), add it to the hook:

```bash
sudo vi /var/www/html/.git/hooks/post-merge
# add inside the for-loop or append:
#   [ -d "$ECCUBE_ROOT/var/myplugin" ] && chown -R "$WEB_USER:$WEB_USER" "$ECCUBE_ROOT/var/myplugin"
```

## Verifying ownership after a pull

```bash
sudo git -c "safe.directory=/var/www/html" -C /var/www/html pull
stat /var/www/html/var | grep -E "Uid|Gid"
# expected owner: apache (OL9) or www-data (Ubuntu)
```

Confirm `.git` remains inaccessible to the web user:

```bash
su -s /bin/sh apache -c "ls /var/www/html/.git"
# expected: Permission denied
```
