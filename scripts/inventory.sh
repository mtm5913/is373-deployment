#!/usr/bin/env bash
# Run as deploy. Read-only, intentionally excludes environment values and key files.
set -eu
printf '\n=== Collected at UTC ===\n'; date -u
printf '\n=== Identity and OS ===\n'; whoami; uname -srm; cat /etc/os-release
printf '\n=== Resources ===\n'; free -m; df -h /
printf '\n=== Docker version and containers ===\n'
docker version --format '{{.Server.Version}}'
docker ps --format '{{.Names}} | {{.Image}} | {{.Ports}}'
printf '\n=== Compose projects ===\n'; docker compose ls
printf '\n=== Listening sockets ===\n'; ss -lntu
printf '\n=== SSH effective settings (sudo may prompt) ===\n'
sudo -n sshd -T 2>/dev/null | grep -E '^(permitrootlogin|passwordauthentication|pubkeyauthentication|kbdinteractiveauthentication) ' || printf 'Effective privileged SSH check pending interactive sudo.\n'
printf '\n=== Firewall ===\n'; sudo -n ufw status 2>/dev/null || printf 'Firewall check pending interactive sudo.\n'
