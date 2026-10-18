#!/usr/bin/env bash
# Apply managed Samba, maintenance, backup, and power settings on the target host.
set -euo pipefail
umask 077
[[ $EUID == 0 ]] || { echo 'Host setup requires root.' >&2; exit 1; }
: "${SETUP_USER:?}" "${DATA_ROOT:?}" "${HOMELAB_ROOT:?}"
[[ $(id -u "$SETUP_USER") != 0 ]] || exit 1
[[ $DATA_ROOT == /* && $DATA_ROOT != / && $HOMELAB_ROOT == /* ]] || exit 1
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
install -d -m 0700 /etc/sisyphus

# Preserve the host's Samba policy and manage only the nas share.
if [[ ! -f /etc/samba/sisyphus.conf ]] && grep -Eq '^\[nas\]' /etc/samba/smb.conf; then
    echo 'An existing [nas] Samba share conflicts; resolve it before applying.' >&2
    exit 1
fi
cp -an /etc/samba/smb.conf /etc/samba/smb.conf.before-sisyphus
cat > /etc/samba/sisyphus.conf <<EOF
[nas]
   path = $DATA_ROOT/nas
   browseable = yes
   read only = no
   guest ok = no
   valid users = $SETUP_USER
   create mask = 0664
   directory mask = 0775
EOF
if ! grep -Fq 'include = /etc/samba/sisyphus.conf' /etc/samba/smb.conf; then
    printf '\ninclude = /etc/samba/sisyphus.conf\n' >> /etc/samba/smb.conf
fi
testparm -s >/dev/null
if [[ -n ${SAMBA_PASSWORD:-} ]]; then
    printf '%s\n%s\n' "$SAMBA_PASSWORD" "$SAMBA_PASSWORD" | smbpasswd -s -a "$SETUP_USER"
else
    echo "Set the Samba password with: sudo smbpasswd -a $SETUP_USER"
fi
systemctl restart smbd

install -m 0755 "$script_dir/maintenance.sh" /usr/local/sbin/sisyphus-maintenance
cat > /etc/cron.d/sisyphus <<'EOF'
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
*/30 * * * * root /usr/local/sbin/sisyphus-maintenance disk
*/10 * * * * root /usr/local/sbin/sisyphus-maintenance containers
*/15 * * * * root /usr/local/sbin/sisyphus-maintenance services
0 */12 * * * root docker system df 2>&1 | logger -t sisyphus-docker
0 4 * * 0 root journalctl --vacuum-time=7d
0 2 * * * root apt-get update >> /var/log/sisyphus-apt.log 2>&1
EOF
if [[ -n ${SMART_DEVICE:-} ]]; then
    [[ $SMART_DEVICE =~ ^/dev/[a-zA-Z0-9/_-]+$ && -b $SMART_DEVICE ]] || { echo 'SMART_DEVICE must be an existing /dev block device.' >&2; exit 1; }
    printf '0 1 1 * * root smartctl -t long %s | logger -t sisyphus-smart\n0 6 * * 0 root smartctl -H %s | logger -t sisyphus-smart\n' "$SMART_DEVICE" "$SMART_DEVICE" >> /etc/cron.d/sisyphus
fi
if [[ ${ENABLE_SURICATA:-false} == true ]]; then
    printf '0 1 * * * root docker compose -p sisyphus-suricata -f %q exec -T suricata suricata-update && docker compose -p sisyphus-suricata -f %q restart suricata\n' "$HOMELAB_ROOT/generated/suricata-compose.yml" "$HOMELAB_ROOT/generated/suricata-compose.yml" >> /etc/cron.d/sisyphus
fi

if [[ ${ENABLE_BACKUPS:-false} == true ]]; then
    : "${BORG_PASSPHRASE:?Set a Borg passphrase before enabling backups}"
    export BORG_REPO="${BORG_REPO:-$DATA_ROOT/backups/borg}"
    [[ $BORG_REPO == /* && $BORG_REPO != / && $BORG_REPO != *$'\n'* ]] || exit 1
    # borg key material stays encrypted; the unattended job's passphrase is root-only.
    printf 'export BORG_REPO=%q\nexport BORG_PASSPHRASE=%q\nDATA_ROOT=%q\nCOMPOSE_FILE=%q\n' \
        "$BORG_REPO" "$BORG_PASSPHRASE" "$DATA_ROOT" "$HOMELAB_ROOT/generated/docker-compose.yml" > /etc/sisyphus/backup.env
    if [[ ! -d $BORG_REPO ]]; then
        mkdir -p "$(dirname "$BORG_REPO")"
        borg init --encryption=repokey "$BORG_REPO"
    else
        borg info "$BORG_REPO" >/dev/null
    fi
    install -m 0755 "$script_dir/backup.sh" /usr/local/sbin/sisyphus-backup
    cat >> /etc/cron.d/sisyphus <<'EOF'
0 3 * * * root /usr/local/sbin/sisyphus-backup >> /var/log/sisyphus-backup.log 2>&1
0 4 1 * * root /usr/local/sbin/sisyphus-backup check >> /var/log/sisyphus-backup.log 2>&1
EOF
fi
chmod 0644 /etc/cron.d/sisyphus
systemctl enable --now cron
if [[ ${DISABLE_SLEEP:-false} == true ]]; then
    systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
    mkdir -p /etc/systemd/logind.conf.d
    printf '[Login]\nHandleLidSwitch=ignore\nHandleLidSwitchDocked=ignore\nHandleLidSwitchExternalPower=ignore\n' > /etc/systemd/logind.conf.d/sisyphus.conf
    echo 'Lid settings take effect after reboot.'
fi
