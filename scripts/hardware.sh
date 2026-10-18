#!/usr/bin/env bash
# Read-only inventory to help choose explicit feature settings.
set -euo pipefail
printf 'CPU: '
awk -F ': ' '/model name/ {print $2; found=1; exit} END {if (!found) print "see lscpu"}' /proc/cpuinfo
printf 'Logical CPUs: %s\n' "$(getconf _NPROCESSORS_ONLN)"
memory_mb=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
printf 'RAM: %s MiB\n\nDisks (choose the secondary data disk deliberately):\n' "$memory_mb"
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL
printf '\nNetwork interfaces (choose one for NETWORK_INTERFACE):\n'
for interface_path in /sys/class/net/*; do
    printf '%s (%s)\n' "${interface_path##*/}" "$(cat "$interface_path/operstate")"
done
printf '\nGraphics devices:\n'
if [[ -d /dev/dri ]]; then
    ls -l /dev/dri
    echo 'JELLYFIN_HW_ACCEL=true can expose these devices; select the matching acceleration mode in Jellyfin.'
else
    echo 'No /dev/dri devices detected; keep JELLYFIN_HW_ACCEL=false.'
fi
printf '\nSuggested starting settings; adjust for workload:\n'
if (( memory_mb < 4096 )); then
    printf 'ENABLE_MONITORING=false\nENABLE_SURICATA=false\nENABLE_DESKTOP=false\nENABLE_JELLYFIN=false\nENABLE_MUSIC=false\n'
else
    printf 'ENABLE_MONITORING=true\nENABLE_SURICATA=false\nENABLE_DESKTOP=false\nENABLE_JELLYFIN=true\nENABLE_MUSIC=true\n'
fi
echo 'Suggestions are a starting point, not a resource guarantee. Suricata and transcoding can require substantial CPU/RAM.'
