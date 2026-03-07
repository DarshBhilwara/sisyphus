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
sudo mkdir /data/configs/suricata/rules                                             
sudo chown -R $USER:$USER /data/configs/suricata 
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
      - SYS_NICE
    volumes:
      - /data/configs/suricata:/etc/suricata
      - /data/logs/suricata:/var/log/suricata
      - /data/configs/suricata/rules:/var/lib/suricata/rules
    command: -i <your network device(en.../wl...)>
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
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=3d"
    restart: unless-stopped
```
Start
```
docker-compose up -d
```

### 6. Grafana
```
cd ~/homelab/monitoring
mkdir grafana
cd grafana
vim docker-compose.yml
```
Insert this
```
services:
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3002:3000"
    volumes:
      - /data/configs/grafana:/var/lib/grafana
    restart: unless-stopped
```
Start
```
docker-compose up -d
```

### 7. Loki
```
cd ~/homelab/monitoring
mkdir loki
cd loki
vim docker-compose.yml
```
Insert this
```
services:
  loki:
    image: grafana/loki:latest
    container_name: loki
    command: -config.file=/etc/loki/loki-config.yml
    ports:
      - "3100:3100"
    volumes:
      - /data/configs/loki:/etc/loki
      - /data/logs/loki:/loki
    restart: unless-stopped
```

### 8. Promtail
```
cd ~/homelab/monitoring
mkdir promtail
cd loki
vim docker-compose.yml
```
Insert this
```
services:
  promtail:
    image: grafana/promtail:latest
    container_name: promtail
    command: -config.file=/etc/promtail/promtail.yml
    volumes:
      - /data/logs:/logs
      - /data/configs/promtail:/etc/promtail
      - /var/log:/var/log
    restart: unless-stopped
```
Start:
```
docker-compose up -d
```

## Setup
### 1. ufw
```
sudo ufw reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow <SSH-PORT>/tcp
```
Allow other services
```
sudo ufw allow 7575/tcp
sudo ufw allow 3001/tcp
sudo ufw allow 8096/tcp
sudo ufw allow 22300/tcp
sudo ufw allow 53/tcp
sudo ufw allow 53/udp
sudo ufw allow 3000/tcp
sudo ufw allow 80/tcp
sudo ufw allow 1514/tcp
sudo ufw allow 1515/tcp
sudo ufw allow 514/udp
sudo ufw allow 5601/tcp
sudo ufw allow in on docker0
sudo ufw allow 8384/tcp
sudo ufw allow 22000/tcp
sudo ufw allow 22000/udp
sudo ufw allow 21027/udp
sudo ufw allow 9091/tcp
```
Logging
```
sudo ufw logging medium
```
Start:
```
sudo ufw enable
```
Check
```
sudo ufw status numbered
```

### 2. Suricata
- Update rules
```
docker exec -it suricata bash
suricata-update
exit
docker restart suricata
```
Test
```
curl http://testmynids.org/uid/index.html
```
Check
```
tail -f /data/logs/suricata/fast.log
```
Should show something like
```
[Classification: Potentially Bad Traffic] 
```

### 3. Adguard
- Go to `http://server-ip:3000` on your client.
- Set up interface on all interfaces at 3000 for web and 53 for DNS server.
- Go to your router setup (something like `http://192.168.1.1`).
- Go to LAN setup
- Change DNS to user defined and to your server IP address.
- Disconnect and reconnect your device to Wi-Fi and check if there are entries on the AdGuard dashboard.

### 4. SIEM
#### Loki
- Set loki permissions `sudo chown -R 10001:10001 /data/logs/loki`
- Loki config at `/data/configs/loki/loki-config.yml`
```
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  replication_factor: 1
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-05-15
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
storage_config:
  filesystem:
    directory: /loki/chunks

limits_config:
  retention_period: 72h

compactor:
  working_directory: /loki/compactor
  compaction_interval: 10m
```
- Restart loki.

- Promtail config at `/data/configs/promtail/promtail.yml`
```
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:

- job_name: suricata
  static_configs:
  - targets:
      - localhost
    labels:
      job: suricata
      __path__: /logs/suricata/*.log

- job_name: system
  static_configs:
  - targets:
      - localhost
    labels:
      job: syslog
      __path__: /var/log/*.log
```

#### Promtail
- Write this in the config file `/data/configs/promtail/promtail.yml`
```
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:

- job_name: suricata
  static_configs:
  - targets:
      - localhost
    labels:
      job: suricata
      __path__: /logs/suricata/*.log

- job_name: system
  static_configs:
  - targets:
      - localhost
    labels:
      job: syslog
      __path__: /var/log/*.log
```
Restart promtail and check logs.

#### Prometheus
- Write this in the `/data/configs/prometheus/prometheus.yml`
```
global:
  scrape_interval: 30s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ['localhost:9090']
```
Restart prometheus and check logs.

