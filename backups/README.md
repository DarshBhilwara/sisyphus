# Backups, Cron Jobs and Scripts

## Installation of softwares required
```
sudo apt install borgbackup rsync smartmontools
```

## Backups
- We have to backup everything except backups in the `/data/backups`
- First, initialize the borg repository with `borg init --encryption=repokey /data/backups/borg` and test access with `borg list /data/backups/borg`
- We will create a script `/usr/local/bin/backup.sh`
```
#!/bin/bash

set -e 

export BORG_REPO=/data/backups/borg
export BORG_PASSPHRASE="yourpassword"

borg create \
  --stats \
  --compression lz4 \
  $BORG_REPO::$(date +%Y-%m-%d-%H%M) \
  /home \
  /data/configs \
  /data/docker \
  /data/logs \
  /data/nas 

borg prune \
  --keep-daily=7 \
  --keep-weekly=4 \
  --keep-monthly=6 \
  $BORG_REPO

borg compact $BORG_REPO
```
- Make it executable `sudo chmod +x /usr/local/bin/backup.sh`

## Scripts
### Disk usage alert script
- We need to check disk usage above 80%
- Save at `/usr/local/bin/diskcheck.sh`
```
#!/bin/bash

df -hP | awk 'NR>1 {print $6" "$5}' | while read mount usage
do
    percent=$(echo "$usage" | tr -d '%')

    if [ "$percent" -gt 80 ]; then
        logger "Disk usage warning: $mount at $usage"
    fi
done
```
- Make it executable with `sudo chmod +x /usr/local/bin/diskcheck.sh`

### Docker Container Monitoring
- We will log if a docker container goes down.
- Create a script at `/usr/local/bin/containercheck.sh`
```
#!/bin/bash

for container in $(docker ps -a --format '{{.Names}}')
do
    status=$(docker inspect -f '{{.State.Running}}' "$container")

    if [ "$status" != "true" ]; then
        logger "Container $container is DOWN"
    fi
done
```
- Make it executable with `sudo chmod +x /usr/local/bin/containercheck.sh`

### Systemd Services Log
- We will log if a systemd service goes down.
- Create a script at `/usr/local/bin/servicecheck.sh`
```
#!/bin/bash

failed=$(systemctl --failed --no-legend)

if [ -n "$failed" ]; then
    logger "Failed systemd services detected"
fi
```
- Make it executable with `sudo chmod +x /usr/local/bin/servicecheck.sh` 

### Docker Disk Usage Report
- We will log docker disk usage
- Create a script at `/usr/local/bin/docker-disk-usage.sh`
```
#!/bin/bash

docker system df | logger
```
- Make it executable with `sudo chmod +x /usr/local/bin/docker-disk-usage.sh` 

## Cron Jobs
- We will edit cron `sudo crontab -e`
- Add the following lines
```
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# for  backing up everyday at 3 am
0 3 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1

# for removing logs every sunday at 4 am
0 4 * * 0 journalctl --vacuum-time=7d 

# for cleaning up docker every sunday at 5 am
0 5 * * 0 docker system prune -af

# update everyday at 2 am
0 2 * * * apt update > /var/log/apt-update.log 2>&1

# diskcheck every 30 minutes
*/30 * * * * /usr/local/bin/diskcheck.sh

# check containers every 10 minute
*/10 * * * * /usr/local/bin/containercheck.sh

# check for failed services every 15 minute
*/15 * * * * /usr/local/bin/servicecheck.sh

# check docker disk usage every half day
0 */12 * * * /usr/local/bin/docker-disk-usage.sh

# do smart extended test at 1am of 1st of every month
0 1 1 * * smartctl -t long /dev/<HDD>

# update borg repository verification on 4am of 1st of every month
0 4 1 * * borg check /data/backups/borg

# update suricata rules daily
0 1 * * * docker exec suricata suricata-update && docker exec suricata kill -USR2 1

# check disk every sunday at 6 am
0 6 * * 0 smartctl -H /dev/<HDD>
```