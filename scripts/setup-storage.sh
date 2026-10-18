#!/usr/bin/env bash
# Optional destructive setup of a secondary disk, never of the Ubuntu OS disk.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Storage setup requires root.' >&2; exit 1; }
: "${DATA_DISK:?Choose an explicit secondary disk, preferably /dev/disk/by-id/...}"
: "${DATA_ROOT:?}"
[[ $DATA_ROOT =~ ^/[a-zA-Z0-9/_-]+$ && $DATA_ROOT != / ]] || { echo 'DATA_ROOT must be a simple absolute mount path.' >&2; exit 1; }
disk=$(readlink -f -- "$DATA_DISK")
[[ -b $disk && $(lsblk -dn -o TYPE "$disk") == disk ]] || { echo 'DATA_DISK must identify a whole physical disk.' >&2; exit 1; }

# Verify disk ancestry and mount state from kernel inventory before any write.
export SISYPHUS_DATA_DISK="$disk"
python3 - <<'PY'
import json, os, subprocess
disk = os.environ['SISYPHUS_DATA_DISK']
inventory = json.loads(subprocess.check_output(['lsblk', '--json', '--paths', '--output', 'NAME,TYPE,MOUNTPOINTS', disk]))
def verify(node):
    mounts = [m for m in node.get('mountpoints', []) if m]
    if mounts:
        raise SystemExit(f'Refusing disk in use: {node["name"]} is mounted at {mounts}')
    device = os.path.basename(os.path.realpath(node['name']))
    holders = '/sys/class/block/' + device + '/holders'
    if os.path.isdir(holders) and os.listdir(holders):
        raise SystemExit(f'Refusing disk with active holders: {node["name"]}')
    for child in node.get('children', []):
        verify(child)
for node in inventory['blockdevices']:
    verify(node)
PY
if [[ ${ALLOW_DISK_ERASE:-false} != true ]]; then
    echo "Storage plan: erase $disk; create vgdata/data using the entire disk; format ext4; mount at $DATA_ROOT."
    echo 'No changes made. Set ALLOW_DISK_ERASE=true only when this is the intended empty/replaceable disk.' >&2
    exit 1
fi
# Check naming/path conflicts before erasing anything.
if vgs vgdata >/dev/null 2>&1; then
    echo 'vgdata already exists; configure storage manually or disable ENABLE_STORAGE_SETUP on reruns.' >&2
    exit 1
fi
if mountpoint -q "$DATA_ROOT"; then
    echo 'DATA_ROOT is already mounted; disable ENABLE_STORAGE_SETUP.' >&2
    exit 1
fi
if [[ -d $DATA_ROOT ]] && [[ -n $(find "$DATA_ROOT" -mindepth 1 -maxdepth 1 -print -quit) ]]; then
    echo 'DATA_ROOT is nonempty; refusing to hide its existing contents.' >&2
    exit 1
fi
if awk -v path="$DATA_ROOT" '$1 !~ /^#/ && $2 == path {found=1} END {exit !found}' /etc/fstab; then
    echo 'DATA_ROOT already has an fstab entry; resolve it before storage setup.' >&2
    exit 1
fi
echo "Provisioning explicitly selected data disk: $disk"
wipefs -a "$disk"
pvcreate "$disk"
vgcreate vgdata "$disk"
lvcreate -l 100%FREE -n data vgdata
mkfs.ext4 /dev/vgdata/data
mkdir -p "$DATA_ROOT"
uuid=$(blkid -s UUID -o value /dev/vgdata/data)
[[ -n $uuid ]]
cp -an /etc/fstab /etc/fstab.before-sisyphus
printf 'UUID=%s %s ext4 defaults,noatime 0 2\n' "$uuid" "$DATA_ROOT" >> /etc/fstab
systemctl daemon-reload
mount "$DATA_ROOT"
echo 'Data volume mounted. Disable ENABLE_STORAGE_SETUP and ALLOW_DISK_ERASE before subsequent runs.'
