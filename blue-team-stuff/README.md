# Blue Team Stuff
- The plan is to have the following blue team stack
- Firewall - `ufw`
- IDS - `Suricata`
- DNS Filtering - `AdGuard`
- SIEM - `wazuh`
- Monitoring - `Prometheus and Grafana`
- Logs - `Loki`

## Installation
Creating directory structure
```
cd /data/configs
sudo mkdir suricata adguard wazuh prometheus grafana loki promtail
cd /data/logs
sudo mkdir suricata wazuh  loki
sudo chown -R $USER:$USER /data/configs/*
sudo chown -R $USER:$USER /data/logs/*
```

### 1. UFW
```
sudo apt install ufw
sudo systemctl enable ufw
```
### 2. Suricata
```
cd ~/homelab/security
mkdir suricata
cd suricata
vim docker-compose.yml
```
Insert this
```
services:
  suricata:
    image: jasonish/suricata:latest
    container_name: suricata
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - /data/configs/suricata:/etc/suricata
      - /data/logs/suricata:/var/log/suricata
    restart: unless-stopped
```
Start:
```
docker-compose up -d
```

### 3. AdGuard
```
cd ~/homelab/security
mkdir adguard
cd adguard
vim docker-compose.yml
```
Insert this
```
services:
  adguard:
    image: adguard/adguardhome:latest
    container_name: adguard
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "80:80"
      - "3000:3000"
    volumes:
      - /data/configs/adguard:/opt/adguardhome/conf
      - /data/logs/adguard:/opt/adguardhome/work
    restart: unless-stopped
```
First, let us make port 53 free 
- Go to `/etc/systemd/resolved.conf`
- Find `#DNSStubListener=yes` and change it to no and remove comment.
- `sudo systemctl restart systemd-resolved`
Start:
```
docker-compose up -d
```
