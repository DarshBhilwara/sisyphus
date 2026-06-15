# Blue Team Stuff
- The plan is to have the following blue team stack
- Firewall - `ufw`
- IDS - `Suricata`
- DNS Filtering - `AdGuard`
- Monitoring - `Prometheus and Grafana`
- Logs - `Loki`
- Exporter - `node-exporter`, `adguard-exporter` - convert information to prometheus metrics.

## Installation
Creating directory structure
```
cd /data/configs
sudo mkdir suricata adguard prometheus grafana loki promtail
cd /data/logs
sudo mkdir suricata loki
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

### 3. Adguard
```
cd ~/homelab/security
mkdir adguard
cd adguard
vim docker-compose.yml
```
Insert this
```
services:
  adguardhome:
    image: adguard/adguardhome:latest
    container_name: adguardhome
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "3000:3000/tcp"
    volumes:
      - /data/configs/adguard:/opt/adguardhome/conf
      - /data/logs/adguard:/opt/adguardhome/work
    restart: unless-stopped
    networks:
      - default
      - proxy
    labels:
      - traefik.enable=true
      - traefik.docker.network=proxy
      - traefik.http.routers.adguard.rule=Host(`adguard.home`)
      - traefik.http.services.adguard.loadbalancer.server.port=3000
networks:
  proxy:
    external: true
```
Start:
```
docker-compose up -d
```

### 4. Monitoring
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
    networks:
      - default
      - proxy
    labels:
      - traefik.enable=true
      - traefik.docker.network=proxy
      - traefik.http.routers.loki.rule=Host(`loki.home`)
      - traefik.http.services.loki.loadbalancer.server.port=3100

  promtail:
    image: grafana/promtail:latest
    container_name: promtail
    command: -config.file=/etc/promtail/promtail.yml
    volumes:
      - /data/logs:/logs
      - /data/configs/promtail:/etc/promtail
      - /var/log:/var/log
      - /data/docker/containers:/data/docker/containers:ro
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3002:3000"
    volumes:
      - /data/configs/grafana:/var/lib/grafana
    restart: unless-stopped
    networks:
      - default
      - proxy
    labels:
      - traefik.enable=true
      - traefik.docker.network=proxy
      - traefik.http.routers.grafana.rule=Host(`grafana.home`)
      - traefik.http.services.grafana.loadbalancer.server.port=3000

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
    networks:
      - default
      - proxy
    labels:
      - traefik.enable=true
      - traefik.docker.network=proxy
      - traefik.http.routers.prometheus.rule=Host(`prometheus.home`)
      - traefik.http.services.prometheus.loadbalancer.server.port=9090

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    restart: unless-stopped
    pid: host
    volumes:
      - /:/host:ro,rslave
    command:
      - '--path.rootfs=/host'

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: cadvisor
    restart: unless-stopped
    ports:
      - "2834:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker:/var/lib/docker:ro

  adguard-exporter:
    image: ghcr.io/henrywhitaker3/adguard-exporter:latest
    container_name: adguard-exporter
    environment:
      - ADGUARD_SERVERS=http://localhost:3000
      - ADGUARD_USERNAMES=youruser
      - ADGUARD_PASSWORDS=yourpw
      - INTERVAL=30s
    ports:
      - "9618:9618"
    restart: unless-stopped

networks:
  proxy:
    external: true
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
sudo ufw allow in on tailscale0 # tailscale
sudo ufw allow <SSH-PORT>/tcp 
```
Allow other services
```
sudo ufw allow from 192.168.1.0/24 to any port 7575 proto tcp # homarr
sudo ufw allow from 192.168.1.0/24 to any port 3001 proto tcp # dashdot
sudo ufw allow from 192.168.1.0/24 to any port 8096 proto tcp # jellyfin
sudo ufw allow from 192.168.1.0/24 to any port 22300 proto tcp # joplin
sudo ufw allow from 192.168.1.0/24 to any port 53 proto tcp # adguard
sudo ufw allow from 192.168.1.0/24 to any port 53 proto udp # adguard
sudo ufw allow from 192.168.1.0/24 to any port 3000 proto tcp # adguard
sudo ufw allow from 192.168.1.0/24 to any port 8088 proto tcp # bookmarks
sudo ufw allow in on docker0 # docker 
sudo ufw allow from 192.168.1.0/24 to any port 3002 proto tcp # grafana
sudo ufw allow from 192.168.1.0/24 to any port 9090 proto tcp # prometheus
sudo ufw allow from 192.168.1.0/24 to any port 2834 proto tcp # cadvisor
sudo ufw allow from 192.168.1.0/24 to any port 9618 proto tcp # adguard exporter
sudo ufw allow from 192.168.1.0/24 to any port 8384 proto tcp # syncthing
sudo ufw allow from 192.168.1.0/24 to any port 80 proto tcp # traefik
sudo ufw allow 22000/tcp
sudo ufw allow 22000/udp
sudo ufw allow 21027/udp
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
- First go to `<server-ip>:3000` 
- Next, set up admin listen interface all at port 3000.
- DNS server listen interface all at port 53.
- Do next 
- Next go to your router settings at `http://192.168.0.1` and set up primary DNS as your server IP address.
- Next, in the router settings, do address reservation of your homelab.
- Next, on the adguard dashboard, go to Filters>DNS blocklists and add any good blocklist.
- Next, go to tailscale DNS settings and under global nameserver, add your server's tailscale IP and turn on override DNS servers.

### 4. Monitoring 
#### Prometheus Config
Add this in `/data/configs/prometheus/prometheus.yml` to connect it with all the required services.
```
global:
  scrape_interval: 30s
  evaluation_interval: 30s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ['localhost:9090']

  - job_name: node-exporter
    static_configs:
      - targets: ['node-exporter:9100']


  - job_name: cadvisor
    static_configs:
      - targets: ['cadvisor:8080']

  - job_name: adguard-exporter
    static_configs:
      - targets: ['adguard-exporter:9618']
```

#### Promtail Config
- Go to `/data/configs/promtail/promtail.yml` and add.
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

- job_name: docker
  static_configs:
    - targets:
      - localhost
      labels:
        job: docker
        __path__: /data/docker/containers/*/*.log
```

#### Loki Config
- Go to `/data/configs/loki/loki-config.yml` and add
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

  ingestion_rate_strategy: global
  ingestion_rate_mb: 16
  ingestion_burst_size_mb: 32

compactor:
  working_directory: /loki/compactor

  compaction_interval: 10m

  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 50

  delete_request_store: filesystem
```

#### Grafana
- First, we add data sources to Grafana(at port 3002), `Connections->Data Sources->Add Data Source->http://loki:3100`
- Next similarly, add prometheus `http://prometheus:9090` 
