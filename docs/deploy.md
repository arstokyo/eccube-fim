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
root, mode 700). After every successful `git pull`, the hook runs two steps:

1. `chown -R $WEB_USER:$WEB_USER $ECCUBE_ROOT` — restores web-user ownership
   on every file and directory in the working tree so Apache and PHP-FPM can
   read (and write where needed) all files regardless of umask or SELinux context.
2. `chown -R root:root $ECCUBE_ROOT/.git && chmod -R go-rwx $ECCUBE_ROOT/.git`
   — immediately re-secures `.git` so only root can access it.

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
