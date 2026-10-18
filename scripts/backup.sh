#!/usr/bin/env bash
set -euo pipefail
umask 077
# shellcheck disable=SC1091
source /etc/sisyphus/backup.env
exec 9>/run/lock/sisyphus-backup.lock
flock -n 9 || exit 0
if [[ ${1:-} == check ]]; then
    exec borg check "$BORG_REPO"
fi
# Pause precisely the running containers to keep databases and app files consistent.
running_output=$(docker compose -f "$COMPOSE_FILE" ps --status running -q)
running=()
if [[ -n $running_output ]]; then mapfile -t running <<< "$running_output"; fi
if (( ${#running[@]} )); then
    trap 'docker start "${running[@]}" >/dev/null' EXIT
    docker stop "${running[@]}" >/dev/null
fi
# Exclude the backup repository even when it lives inside a source tree.
set +e
borg create --stats --compression lz4 --exclude "$BORG_REPO" \
    "$BORG_REPO::$(date -u +%Y-%m-%d-%H%M%S)" \
    /home /etc "$DATA_ROOT/configs" "$DATA_ROOT/logs" "$DATA_ROOT/nas"
backup_status=$?
set -e
if (( ${#running[@]} )); then
    docker start "${running[@]}" >/dev/null
    trap - EXIT
fi
# Borg 1.x exit status 1 is a completed backup with warnings, 2+ is a failure.
(( backup_status < 2 )) || exit "$backup_status"
borg prune --keep-daily=7 --keep-weekly=4 --keep-monthly=6 "$BORG_REPO"
borg compact "$BORG_REPO"
exit "$backup_status"
