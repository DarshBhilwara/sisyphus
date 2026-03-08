# Backups and Cron Jobs

## Installation of softwares required
```
sudo apt install borgbackup rsync smartmontools
```

## Backups
- We have to backup everything except backups and nas in the `/data`
- We will create a script `/usr/local/bin/backup.sh`
```
#!/bin/bash

export BORG_REPO=/data/backups/borg
export BORG_PASSPHRASE="yourpassword"

borg create \
--compression lz4 \
$BORG_REPO::$(date +%Y-%m-%d-%H%M) \
/home \
/data/configs \
/data/docker \
/data/logs

borg prune \
--keep-daily=7 \
--keep-weekly=4 \
--keep-monthly=6 \
$BORG_REPO
```
- Make it executable `sudo chmod +x /usr/local/bin/backup.sh`

## Cron Jobs
- We will edit cron `sudo crontab -e`
- Add the following lines
```
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# for  backing up everyday at 3 am
0 3 * * * /usr/local/bin/backup.sh   

# for removing logs every sunday at 4 am
0 4 * * 0 journalctl --vacuum-time=7d 

# for cleaning up docker every sunday at 5 am
0 5 * * 0 docker system prune -af

# update everyday at 2 am
0 2 * * * apt update && apt -y upgrade

# restart containers every sunday at 8 am
0 8 * * 0 docker restart $(docker ps -q)

# diskcheck every 30 minutes
*/30 * * * * /usr/local/bin/diskcheck.sh

# update suricata rules daily
0 1 * * * docker exec suricata suricata-update && docker exec suricata kill -USR2 1

# check disk every sunday at 6 am
0 6 * * 0 smartctl -H /dev/<HDD>
```

### Disk usage alert script
- We need to check disk usage above 80%
- Save at `/usr/local/bin/diskcheck.sh`
```
#!/bin/bash

usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')

if [ "$usage" -gt 80 ]; then
  echo "Disk usage above 80%" | logger
fi
```
