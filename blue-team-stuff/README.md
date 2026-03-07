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
### 4. Wazuh
```
cd ~/homelab/security
mkdir wazuh
cd wazuh
vim docker-compose.yml
```
Insert this
```
services:
  wazuh.indexer:
    image: wazuh/wazuh-indexer:4.14.3
    container_name: wazuh-indexer
    hostname: wazuh-indexer
    restart: unless-stopped
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
      - bootstrap.memory_lock=true
    ulimits:
      memlock:
        soft: -1
        hard: -1
    volumes:
      - /data/configs/wazuh/indexer:/usr/share/wazuh-indexer/data

  wazuh.manager:
    image: wazuh/wazuh-manager:4.14.3
    container_name: wazuh-manager
    hostname: wazuh-manager
    restart: unless-stopped
    depends_on:
      - wazuh.indexer
    ports:
      - "1514:1514/tcp"
      - "1515:1515/tcp"
      - "514:514/udp"
      - "55000:55000"
    environment:
      - INDEXER_URL=https://wazuh-indexer:9200
      - INDEXER_USERNAME=admin
      - INDEXER_PASSWORD=SecretPassword
      - FILEBEAT_SSL_VERIFICATION_MODE=none
    volumes:
      - /data/configs/wazuh/manager:/var/ossec/etc
      - /data/logs/wazuh:/var/ossec/logs

  wazuh.dashboard:
    image: wazuh/wazuh-dashboard:4.14.3
    container_name: wazuh-dashboard
    hostname: wazuh-dashboard
    restart: unless-stopped
    depends_on:
      - wazuh.indexer
      - wazuh.manager
    ports:
      - "5601:5601"
    environment:
      - OPENSEARCH_HOSTS=https://wazuh-indexer:9200
      - WAZUH_API_URL=https://wazuh-manager
      - API_USERNAME=wazuh
      - API_PASSWORD=wazuh
    volumes:
      - /data/configs/wazuh/dashboard:/usr/share/wazuh-dashboard/data

networks:
  default:
    name: wazuh-net
```
Start
```
docker-compose up -d
```

### 5. Prometheus
```
cd ~/homelab/monitoring
mkdir prometheus
cd prometheus
vim docker-compose.yml
```
Insert this
```
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - /data/configs/prometheus:/etc/prometheus
      - /data/logs/prometheus:/prometheus
    restart: unless-stopped
```
Start
```
docker-compose up -d
```

