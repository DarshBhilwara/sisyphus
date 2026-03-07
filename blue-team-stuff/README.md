# Blue Team Stuff
- The plan is to have the following blue team stack
- Firewall - `ufw`
- IDS - `Suricata`
- DNS Filtering - `AdGuard`
- SIEM - `splunk`
- Monitoring - `Prometheus and Grafana`
- Logs - `Loki`

## Installation
Creating directory structure
```
cd /data/configs
sudo mkdir suricata adguard splunk prometheus grafana loki promtail
cd /data/logs
sudo mkdir suricata splunk  loki
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

### 4. Splunk
```
cd  ~/homelab/security
mkdir splunk
cd splunk
vim docker-compose.yml
```
Insert this
```
services:
  splunk:
    image: splunk/splunk:latest
    container_name: splunk
    environment:
      - SPLUNK_GENERAL_TERMS=--accept-sgt-current-at-splunk-com
      - SPLUNK_START_ARGS=--accept-license
      - SPLUNK_PASSWORD=splunkpassword
      - SPLUNK_HEC_TOKEN=suricata-token
      - SPLUNK_ENABLE_LISTEN=9997
    ports:
      - "8000:8000"
      - "8088:8088"
      - "9997:9997"
    volumes:
      - /data/configs/splunk:/opt/splunk/etc
      - /data/logs/splunk:/opt/splunk/var
    restart: unless-stopped
```
Start
```
docker-compose up -d
```

### Splunk Forwarder
```
cd ~/homelab/security
mkdir splunk-forwarder
cd splunk-forwarder
vim docker-compose.yml
```
Insert
```
services:
  splunk-forwarder:
    image: splunk/universalforwarder:latest
    container_name: splunk-forwarder
    environment:
      - SPLUNK_START_ARGS=--accept-license
      - SPLUNK_PASSWORD=fwdpwd
      - SPLUNK_FORWARD_SERVER=splunk:9997
    volumes:
      - /data/logs/suricata:/logs/suricata
    restart: unless-stopped
```
Start
```
docker-compose up -d
```

### 5. Loki
```
cd ~/homelab/monitoring
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

  promtail:
    image: grafana/promtail:latest
    container_name: promtail
    command: -config.file=/etc/promtail/promtail.yml
    volumes:
      - /data/logs:/logs
      - /data/configs/promtail:/etc/promtail
      - /var/log:/var/log
    restart: unless-stopped

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

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3002:3000"
    volumes:
      - /data/configs/grafana:/var/lib/grafana
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
sudo ufw allow from 192.168.1.0/24 to any port 7575
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
sudo ufw allow 8000/tcp
sudo ufw allow 8088/tcp
sudo ufw allow 9997/tcp
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

- job_name: node
  static_configs:
    - targets: ['host.docker.internal:9100']
```
- Fix settings
```
sudo mkdir -p /data/logs/prometheus
sudo chown -R 65534:65534 /data/logs/prometheus
sudo chmod -R 775 /data/logs/prometheus
```
- Restart prometheus and check logs.

#### Grafana 
- Make the permissions correct `sudo chown -R 472:472 /data/configs/grafana`

## Connecting it together
- Open grafana `http://server-ip:3002`
- Log in with `admin:admin`
- Go to Connections and Add Connection and search for Loki and make the URL `http://loki:3100`
- Next, add another connection and search for Prometheus and make the URL `http://prometheus:9090`
