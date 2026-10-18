#!/usr/bin/env bash
set -euo pipefail
case ${1:-} in
    disk)
        df -P | awk 'NR>1 {gsub(/%/, "", $5); if ($5 > 80) print "Disk usage warning: " $6 " at " $5 "%"}' | logger -t sisyphus
        ;;
    containers)
        docker ps -a --filter label=com.docker.compose.project=sisyphus --format '{{.Names}} {{.State}}' |
            awk '$2 != "running" {print "Container " $1 " is " $2}' | logger -t sisyphus
        ;;
    services) systemctl --failed --no-legend | logger -t sisyphus ;;
    *) echo 'Usage: sisyphus-maintenance {disk|containers|services}' >&2; exit 2 ;;
esac
