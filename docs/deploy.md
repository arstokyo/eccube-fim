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

## SSH deploy key setup

Because all pulls run as root, the SSH key used for authentication must be
accessible to root. The installer warns you at install time if it detects an
SSH remote and no key in `/root/.ssh/`. Choose whichever option fits your setup:

### Option A — reuse the web user's existing deploy key (quickest)

Tell root's SSH client where to find the key already registered with your Git
hosting provider. The key may be in the web user's home directory or in a
shared httpd location — check the install warning for the detected path, or
look in these common locations:

| OS | Typical key location |
|----|---------------------|
| Oracle Linux 9 | `/usr/share/httpd/.ssh/` or `/etc/httpd/.ssh/` |
| Ubuntu 24.04 | `/var/www/.ssh/` or `~www-data/.ssh/` |

```bash
mkdir -p /root/.ssh && chmod 700 /root/.ssh
cat >> /root/.ssh/config <<'EOF'
Host *
    IdentityFile /usr/share/httpd/.ssh/id_ed25519
EOF
chmod 600 /root/.ssh/config
```

Replace the `IdentityFile` path with the actual key path on your server.

### Option B — generate a dedicated root deploy key (most isolated)

```bash
ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N ''
cat /root/.ssh/id_ed25519.pub
```

Add the printed public key to your Git hosting provider as an additional
deploy key (GitHub → Settings → Deploy keys, GitLab → Settings → Repository
→ Deploy keys).

### Option C — forward your SSH agent (no key changes on server)

If you connect to the server with SSH agent forwarding enabled (`ssh -A`),
pass your agent socket through sudo:

```bash
sudo -E git -c "safe.directory=/var/www/html" -C /var/www/html pull
```

`-E` preserves `SSH_AUTH_SOCK` so git reaches your local agent. This requires
`Defaults env_keep += "SSH_AUTH_SOCK"` in `/etc/sudoers`.

### Locating the web user's existing key

If you are unsure where the deploy key lives:

```bash
# Check what key the web user's SSH agent knows about
sudo -u apache ssh-add -l 2>/dev/null

# List candidate directories
ls /usr/share/httpd/.ssh/ /etc/httpd/.ssh/ ~apache/.ssh/ 2>/dev/null
```

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
