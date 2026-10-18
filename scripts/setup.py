#!/usr/bin/env python3
"""Render and manage the Sisyphus Ubuntu homelab setup."""
import json
import os
import pathlib
import pwd
import shutil
import subprocess
import sys
import ipaddress
os.umask(0o077)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = pathlib.Path(os.environ.get("DATA_ROOT", "/data"))
BASE = pathlib.Path(os.environ.get("HOMELAB_ROOT", str(pathlib.Path.home() / "homelab")))
USER = os.environ.get("SETUP_USER", os.environ.get("SUDO_USER", ""))
UID = pwd.getpwnam(USER).pw_uid if USER and any(p.pw_name == USER for p in pwd.getpwall()) else 1000
GID = pwd.getpwnam(USER).pw_gid if USER and any(p.pw_name == USER for p in pwd.getpwall()) else 1000
LAN = os.environ.get("LAN_IP", "127.0.0.1")
IFACE = os.environ.get("NETWORK_INTERFACE", "")
KEY = os.environ.get("HOMARR_SECRET_ENCRYPTION_KEY", "")
HOSTS = ["homarr", "syncthing", "joplin", "bookmarksman", "jellyfin", "dashdot", "vaultwarden", "navidrome", "traefik", "adguard", "grafana", "loki", "prometheus"]

def run(args, **kwargs):
    subprocess.run(args, check=True, **kwargs)

def write(path, content):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content)

def generated(path, content):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    os.chmod(path, 0o600)

def initialize_host_dirs():
    owners = {name: f"{UID}:{GID}" for name in (
        "configs/syncthing", "configs/navidrome", "configs/beets", "configs/jellyfin",
        "configs/jellyfin/cache", "nas", "nas/music", "nas/phone-backup", "nas/media",
        "nas/media/movies", "nas/media/tv", "nas/media/personal")}
    owners.update({"configs/bookmarksman": "999:999", "configs/joplin/postgres": "999:999", "configs/grafana": "472:472",
                   "logs/prometheus": "65534:65534", "logs/loki": "10001:10001"})
    # Explicit modes avoid inheriting the private render umask on shared configs.
    paths = [DATA] + [DATA / p.relative_to(BASE / "generated/data-dirs")
                      for p in (BASE / "generated/data-dirs").rglob("*") if p.is_dir()]
    for path in sorted(paths, key=lambda p: len(p.parts)):
        if subprocess.run(["sudo", "test", "-d", str(path)]).returncode == 0:
            continue
        relative = str(path.relative_to(DATA))
        owner = owners.get(relative, "0:0")
        mode = {"configs/joplin/postgres": "0700", "configs/bookmarksman": "0750"}.get(relative, "0755")
        run(["sudo", "install", "-d", "-m", mode, "-o", owner.split(":")[0],
             "-g", owner.split(":")[1], str(path)])

def validate_host_settings():
    account = pwd.getpwnam(USER)
    if account.pw_uid == 0 or account.pw_uid != os.getuid():
        raise SystemExit("Run as the configured nonroot SETUP_USER.")
    for value in (str(DATA), str(BASE), os.environ.get("DOCKER_ROOT", "/data/docker")):
        if not pathlib.Path(value).is_absolute() or value == "/" or any(c in value for c in "\n\r%"):
            raise SystemExit("Data, Docker, and homelab paths must be absolute non-root paths without newlines or percent signs.")
    if ipaddress.ip_address(LAN).version != 4:
        raise SystemExit("LAN_IP must be a host IPv4 address.")
    for name in ("JOPLIN_DB_PASSWORD", "ADGUARD_PASSWORD", "VAULTWARDEN_ADMIN_TOKEN", "SAMBA_PASSWORD"):
        value = os.environ.get(name, "")
        if not value or value.startswith("replace-"):
            raise SystemExit(f"Set a unique value for {name} in setup.env.")
    if KEY == "0123456789abcdef" * 4:
        raise SystemExit("Replace the example Homarr encryption key with a generated key.")
    if os.environ.get("ENABLE_BACKUPS", "false").lower() == "true":
        value = os.environ.get("BORG_PASSPHRASE", "")
        if not value or value.startswith("replace-"):
            raise SystemExit("Set a unique BORG_PASSPHRASE before enabling backups.")
    if os.environ.get("JELLYFIN_HW_ACCEL", "false").lower() == "true" and not pathlib.Path("/dev/dri").exists():
        raise SystemExit("JELLYFIN_HW_ACCEL requires /dev/dri on this host.")
    if os.environ.get("ENABLE_SURICATA", "false").lower() == "true" and (not IFACE or not (pathlib.Path("/sys/class/net") / IFACE).is_dir()):
        raise SystemExit("ENABLE_SURICATA requires an existing NETWORK_INTERFACE.")
    if (os.environ.get("REQUIRE_DATA_MOUNT", "true").lower() == "true"
            and os.environ.get("ENABLE_STORAGE_SETUP", "false").lower() != "true"
            and subprocess.run(["mountpoint", "-q", str(DATA)]).returncode != 0):
        raise SystemExit("DATA_ROOT must already be mounted; configure storage, or explicitly set REQUIRE_DATA_MOUNT=false for OS-disk storage.")

def install_user_configs():
    target = pathlib.Path(pwd.getpwnam(USER).pw_dir) / ".config"
    for source in (ROOT / ".config").rglob("*"):
        if source.is_file() and source.suffix != ".log":
            destination = target / source.relative_to(ROOT / ".config")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copy2(source, destination)

def render():
    if not USER:
        raise SystemExit("SETUP_USER is required (the non-root account that owns/runs the lab).")
    if len(KEY) != 64 or any(c not in "0123456789abcdefABCDEF" for c in KEY):
        raise SystemExit("HOMARR_SECRET_ENCRYPTION_KEY must be 64 hexadecimal characters.")
    target = BASE / "generated"
    # Quote env values as JSON strings, valid in compose's YAML subset.
    def q(v): return json.dumps(str(v).replace("$", "$$"))
    gpu_groups = sorted({device.stat().st_gid for device in pathlib.Path("/dev/dri").glob("*")
                         if device.is_char_device()})
    yaml = f'''name: sisyphus
services:
  traefik:
    image: traefik:v3.7
    command: ["--api.insecure=true", "--providers.docker=true", "--providers.docker.exposedbydefault=false", "--entrypoints.web.address=:80"]
    ports: [{q(LAN + ':80:80')}, {q(LAN + ':8080:8080')}]
    volumes: ["/var/run/docker.sock:/var/run/docker.sock:ro"]
    networks: [proxy]
    restart: unless-stopped
  homarr:
    image: ghcr.io/homarr-labs/homarr:latest
    environment: {{ SECRET_ENCRYPTION_KEY: {q(KEY)} }}
    ports: [{q(LAN + ':7575:7575')}]
    volumes: [{q(str(DATA / 'configs/homarr') + ':/appdata')}, "/var/run/docker.sock:/var/run/docker.sock"]
    restart: unless-stopped
  syncthing:
    image: syncthing/syncthing:latest
    user: {q(f"{UID}:{GID}")}
    ports: [{q(LAN + ':8384:8384')}, "22000:22000/tcp", "22000:22000/udp"]
    volumes: [{q(str(DATA / 'configs/syncthing') + ':/var/syncthing/config')}, {q(str(DATA / 'nas/phone-backup') + ':/var/syncthing/phone')}]
    restart: unless-stopped
  joplin-db:
    image: postgres:16
    environment: {{ POSTGRES_USER: joplin, POSTGRES_PASSWORD: {q(os.environ.get('JOPLIN_DB_PASSWORD', 'CHANGE_ME'))}, POSTGRES_DB: joplindb }}
    volumes: [{q(str(DATA / 'configs/joplin/postgres') + ':/var/lib/postgresql/data')}]
    restart: unless-stopped
  joplin:
    image: joplin/server:latest
    depends_on: [joplin-db]
    ports: [{q(LAN + ':22300:22300')}]
    environment: {{ APP_PORT: "22300", APP_BASE_URL: {q(os.environ.get('JOPLIN_BASE_URL', 'http://joplin.home'))}, DB_CLIENT: pg, POSTGRES_HOST: joplin-db, POSTGRES_PORT: "5432", POSTGRES_USER: joplin, POSTGRES_PASSWORD: {q(os.environ.get('JOPLIN_DB_PASSWORD', 'CHANGE_ME'))}, POSTGRES_DATABASE: joplindb }}
    restart: unless-stopped
  bookmarksman:
    image: darshbhilwara/bookmarksman:1.0.0
    container_name: bookmarksman
    ports: [{q(LAN + ':1024:8080')}]
    environment: {{ BOOKMARKSMAN_DATA: /data/profiles }}
    volumes: [{q(str(DATA / 'configs/bookmarksman') + ':/data')}]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8080/api/health', timeout=2)"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s
  jellyfin:
    image: jellyfin/jellyfin:latest
    profiles: [media]
    user: {q(f"{UID}:{GID}")}
    ports: [{q(LAN + ':8096:8096')}]
    {('devices: ["/dev/dri:/dev/dri"]' if os.environ.get('JELLYFIN_HW_ACCEL', 'false').lower() == 'true' else '# hardware acceleration disabled')}
    {('group_add: ' + json.dumps([str(g) for g in gpu_groups]) if os.environ.get('JELLYFIN_HW_ACCEL', 'false').lower() == 'true' else '# no additional GPU groups')}
    volumes: [{q(str(DATA / 'configs/jellyfin') + ':/config')}, {q(str(DATA / 'configs/jellyfin/cache') + ':/cache')}, {q(str(DATA / 'nas') + ':/nas')}]
    restart: unless-stopped
  dashdot:
    image: mauricenino/dashdot:latest
    ports: [{q(LAN + ':3001:3001')}]
    volumes: ["/:/mnt/host:ro"]
    restart: unless-stopped
  vaultwarden:
    image: vaultwarden/server:latest
    ports: [{q('127.0.0.1:2852:80')}]
    environment: {{ DOMAIN: {q(os.environ.get('VAULTWARDEN_DOMAIN', 'http://localhost:2852'))}, SIGNUPS_ALLOWED: {q(os.environ.get('VAULTWARDEN_SIGNUPS_ALLOWED', 'false'))}, ADMIN_TOKEN: {q(os.environ.get('VAULTWARDEN_ADMIN_TOKEN', 'SET_VAULTWARDEN_ADMIN_TOKEN'))} }}
    volumes: [{q(str(DATA / 'configs/vaultwarden') + ':/data')}]
    restart: unless-stopped
  navidrome:
    image: deluan/navidrome:latest
    profiles: [music]
    user: {q(f"{UID}:{GID}")}
    ports: [{q(LAN + ':4533:4533')}]
    environment: {{ ND_SCANSCHEDULE: "1h", ND_SESSIONTIMEOUT: "24h" }}
    volumes: [{q(str(DATA / 'configs/navidrome') + ':/data')}, {q(str(DATA / 'nas/music') + ':/music:ro')}]
    restart: unless-stopped
  beets:
    image: lscr.io/linuxserver/beets:latest
    profiles: [music]
    environment: {{ PUID: {q(UID)}, PGID: {q(UID)}, TZ: {q(os.environ.get('TZ', 'Asia/Kolkata'))} }}
    ports: [{q(LAN + ':8337:8337')}]
    volumes: [{q(str(DATA / 'configs/beets') + ':/config')}, {q(str(DATA / 'nas/music') + ':/music')}]
    restart: unless-stopped
  adguard:
    image: adguard/adguardhome:latest
    profiles: [monitoring]
    ports: [{q(LAN + ':53:53/tcp')}, {q(LAN + ':53:53/udp')}, {q(LAN + ':3000:3000/tcp')}, {q(LAN + ':3003:80/tcp')}]
    volumes: [{q(str(DATA / 'configs/adguard') + ':/opt/adguardhome/conf')}, {q(str(DATA / 'logs/adguard') + ':/opt/adguardhome/work')}]
    restart: unless-stopped
  loki:
    image: grafana/loki:latest
    profiles: [monitoring]
    command: ["-config.file=/etc/loki/loki-config.yml"]
    ports: [{q(LAN + ':3100:3100')}]
    volumes: [{q(str(DATA / 'configs/loki') + ':/etc/loki')}, {q(str(DATA / 'logs/loki') + ':/loki')}]
    restart: unless-stopped
  prometheus:
    image: prom/prometheus:latest
    profiles: [monitoring]
    command: ["--config.file=/etc/prometheus/prometheus.yml", "--storage.tsdb.retention.time=3d"]
    ports: [{q(LAN + ':9090:9090')}]
    volumes: [{q(str(DATA / 'configs/prometheus') + ':/etc/prometheus')}, {q(str(DATA / 'logs/prometheus') + ':/prometheus')}]
    restart: unless-stopped
  grafana:
    image: grafana/grafana:latest
    profiles: [monitoring]
    ports: [{q(LAN + ':3002:3000')}]
    volumes: [{q(str(DATA / 'configs/grafana') + ':/var/lib/grafana')}, {q(str(DATA / 'configs/grafana/provisioning') + ':/etc/grafana/provisioning:ro')}]
    restart: unless-stopped
  alloy:
    image: grafana/alloy:latest
    profiles: [monitoring]
    command: ["run", "/etc/alloy/config.alloy", "--storage.path=/var/lib/alloy/data"]
    volumes: ["alloy-storage:/var/lib/alloy/data", {q(str(DATA / 'configs/alloy/config.alloy') + ':/etc/alloy/config.alloy:ro')}, "/var/log:/var/log:ro", {q(str(DATA / 'logs') + ':/logs:ro')}, {q(str(pathlib.Path(os.environ.get('DOCKER_ROOT', '/data/docker')) / 'containers') + ':/var/lib/docker/containers:ro')}]
    restart: unless-stopped
  node-exporter:
    image: prom/node-exporter:latest
    profiles: [monitoring]
    pid: host
    command: ["--path.rootfs=/host"]
    volumes: ["/:/host:ro,rslave"]
    restart: unless-stopped
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    profiles: [monitoring]
    ports: [{q(LAN + ':2834:8080')}]
    volumes: ["/:/rootfs:ro", "/var/run:/var/run:ro", "/sys:/sys:ro", {q(str(pathlib.Path(os.environ.get('DOCKER_ROOT', '/data/docker')))+':/var/lib/docker:ro')}]
    restart: unless-stopped
  adguard-exporter:
    image: ghcr.io/henrywhitaker3/adguard-exporter:latest
    profiles: [monitoring]
    environment: {{ ADGUARD_SERVERS: "http://adguard:80", ADGUARD_USERNAMES: {q(os.environ.get('ADGUARD_USERNAME', 'admin'))}, ADGUARD_PASSWORDS: {q(os.environ.get('ADGUARD_PASSWORD', 'SET_IN_SETUP_ENV'))}, INTERVAL: "30s" }}
    ports: [{q(LAN + ':9618:9618')}]
    restart: unless-stopped
volumes:
  alloy-storage: {{}}
networks:
  proxy:
    name: proxy
'''
    generated(target / "docker-compose.yml", yaml)
    route_ports = {"homarr": 7575, "syncthing": 8384, "joplin": 22300, "bookmarksman": 8080,
                   "jellyfin": 8096, "dashdot": 3001, "navidrome": 4533,
                   "adguard": 80, "grafana": 3000, "loki": 3100, "prometheus": 9090}
    for service, port in route_ports.items():
        marker = f"  {service}:\n"
        start = yaml.index(marker) + len(marker)
        candidates = [yaml.find(f"\n  {other}:\n", start) for other in ("traefik", "homarr", "syncthing", "joplin-db", "joplin", "bookmarksman", "jellyfin", "dashdot", "vaultwarden", "navidrome", "beets", "adguard", "loki", "prometheus", "grafana", "alloy", "node-exporter", "adguard-exporter", "networks") if yaml.find(f"\n  {other}:\n", start) >= 0]
        end = min(candidates) if candidates else len(yaml)
        labels = (f"    networks: [default, proxy]\n    labels:\n"
                  f"      traefik.enable: \"true\"\n"
                  f"      traefik.docker.network: \"proxy\"\n"
                  f"      traefik.http.routers.{service}.rule: \"Host(`{service}.home`)\"\n"
                  f"      traefik.http.services.{service}.loadbalancer.server.port: \"{port}\"\n")
        if service == "bookmarksman":
            labels += '      traefik.http.services.bookmarksman.loadbalancer.healthcheck.path: "/api/health"\n'
        yaml = yaml[:end] + "\n" + labels + yaml[end:]
    generated(target / "docker-compose.yml", yaml)
    generated(target / "prometheus.yml", f'''global:\n  scrape_interval: 15s\nscrape_configs:\n  - job_name: prometheus\n    static_configs: [{{targets: ["prometheus:9090"]}}]\n  - job_name: node\n    static_configs: [{{targets: ["node-exporter:9100"]}}]\n  - job_name: adguard\n    static_configs: [{{targets: ["adguard-exporter:9618"]}}]\n''')
    generated(target / "loki-config.yml", '''auth_enabled: false\nserver:\n  http_listen_port: 3100\ncommon:\n  path_prefix: /loki\n  storage:\n    filesystem:\n      chunks_directory: /loki/chunks\n      rules_directory: /loki/rules\n  replication_factor: 1\n  ring:\n    kvstore:\n      store: inmemory\nschema_config:\n  configs:\n    - from: 2024-01-01\n      store: tsdb\n      object_store: filesystem\n      schema: v13\n      index:\n        prefix: index_\n        period: 24h\n''')
    # Seed configuration only when absent so reruns never replace operator edits.
    generated(target / "configs/prometheus/prometheus.yml", (target / "prometheus.yml").read_text())
    generated(target / "configs/loki/loki-config.yml", (target / "loki-config.yml").read_text())
    generated(target / "configs/promtail/promtail.yml", f'''server:\n  http_listen_port: 9080\n  grpc_listen_port: 0\npositions:\n  filename: /tmp/positions.yaml\nclients:\n  - url: http://{LAN}:3100/loki/api/v1/push\nscrape_configs:\n  - job_name: system\n    static_configs:\n      - targets: [localhost]\n        labels:\n          job: varlogs\n          __path__: /var/log/**/*.log\n''')
    generated(target / "configs/alloy/config.alloy", '''local.file_match "system_logs" {\n  path_targets = [{"__path__" = "/var/log/**/*.log", "job" = "varlogs"}, {"__path__" = "/logs/**/*.json", "job" = "suricata"}, {"__path__" = "/var/lib/docker/containers/*/*.log", "job" = "docker"}]\n}\nloki.source.file "system_logs" {\n  targets = local.file_match.system_logs.targets\n  forward_to = [loki.write.local.receiver]\n}\nloki.write "local" {\n  endpoint { url = "http://loki:3100/loki/api/v1/push" }\n}\n''')
    generated(target / "configs/grafana/provisioning/datasources/datasources.yml", '''apiVersion: 1\ndatasources:\n  - name: Prometheus\n    type: prometheus\n    access: proxy\n    url: http://prometheus:9090\n    isDefault: true\n  - name: Loki\n    type: loki\n    access: proxy\n    url: http://loki:3100\n''')
    generated(target / "configs/beets/config.yaml", '''plugins: [musicbrainz, fetchart, embedart, convert, scrub, replaygain, lastgenre, chroma, web, lyrics]\ndirectory: /music\nlibrary: /config/musiclibrary.db\nart_filename: albumart\nthreaded: yes\noriginal_date: yes\nper_disc_numbering: no\npaths:\n  default: $albumartist/$album%aunique{}/$track - $title\n  singleton: Non-Album/$artist - $title\n  comp: Compilations/$album%aunique{}/$track - $title\nimport:\n  write: yes\n  copy: no\n  move: no\n  resume: ask\n  incremental: yes\n  quiet_fallback: skip\n  timid: no\n  log: /config/beet.log\nfetchart: {auto: yes}\nembedart: {auto: yes}\nlastgenre: {auto: yes, source: album}\nlyrics:\n  auto: yes\n  sources: [lrclib, lrcmux, genius]\n  synced: yes\nweb: {host: 0.0.0.0, port: 8337}\n''')
    
    for p in ["nas", "nas/phone-backup", "nas/media", "nas/media/movies", "nas/media/tv", "nas/media/personal", "nas/music", "configs/homarr", "configs/syncthing", "configs/joplin/postgres", "configs/bookmarksman", "configs/jellyfin", "configs/jellyfin/cache", "configs/vaultwarden", "configs/navidrome", "configs/beets", "configs/grafana", "configs/grafana/provisioning/datasources", "configs/prometheus", "configs/loki", "configs/adguard", "configs/alloy", "configs/suricata/rules", "logs/suricata", "logs/loki", "logs/adguard", "logs/prometheus", "backups"]:
        (target / "data-dirs" / p).mkdir(parents=True, exist_ok=True)
    generated(target / "suricata-compose.yml", f'''services:\n  suricata:\n    image: jasonish/suricata:latest\n    network_mode: host\n    cap_add: [NET_ADMIN, NET_RAW, SYS_NICE]\n    volumes: [{q(str(DATA / 'configs/suricata') + ':/etc/suricata')}, {q(str(DATA / 'logs/suricata') + ':/var/log/suricata')}, {q(str(DATA / 'configs/suricata/rules') + ':/var/lib/suricata/rules')}]\n    command: ["-i", {q(IFACE or 'SET_NETWORK_INTERFACE')}]\n    restart: unless-stopped\n''')
    print(f"Rendered compose and initial configs under {target}; no host packages or /data files were changed.")
    os.chmod(target / "docker-compose.yml", 0o600)
    os.chmod(target / "suricata-compose.yml", 0o600)

def main(action):
    if action == "render":
        render(); return
    if action == "apply":
        if os.geteuid() == 0: raise SystemExit("Run apply as SETUP_USER; the script uses sudo for system packages only.")
        validate_host_settings()
        render()
        root = pathlib.Path("/var/lib/docker")
        desired = pathlib.Path(os.environ.get("DOCKER_ROOT", "/data/docker"))
        run(["sudo", "apt-get", "update"])
        run(["sudo", "apt-get", "install", "-y", "ufw", "curl", "lvm2", "e2fsprogs", "util-linux", "samba", "borgbackup", "rsync", "smartmontools", "cron", "git", "ripgrep", "fd-find", "build-essential", "python3", "nodejs", "npm", "tmux", "btop", "htop"])
        if os.environ.get("ENABLE_STORAGE_SETUP", "false").lower() == "true":
            preserve = "DATA_ROOT,DATA_DISK,ALLOW_DISK_ERASE"
            run(["sudo", f"--preserve-env={preserve}", "bash", str(ROOT / "scripts/setup-storage.sh")])
        initialize_host_dirs()
        daemon = pathlib.Path("/etc/docker/daemon.json")
        if daemon.exists():
            raw = subprocess.run(["sudo", "cat", str(daemon)], check=True, capture_output=True, text=True).stdout
            cfg = json.loads(raw)
            if cfg.get("data-root", str(root)) != str(desired):
                raise SystemExit("Existing Docker data-root conflicts with DOCKER_ROOT; resolve manually before apply.")
        elif desired != root:
            existing = subprocess.run(["sudo", "find", str(root), "-mindepth", "1", "-print", "-quit"], capture_output=True, text=True)
            if root.exists() and existing.stdout.strip():
                raise SystemExit("Docker already has data in /var/lib/docker; refusing migration. Configure it manually.")
            generated(BASE / "generated/daemon.json", json.dumps({"data-root": str(desired)}, indent=2) + "\n")
            run(["sudo", "mkdir", "-p", "/etc/docker", str(desired)])
            run(["sudo", "install", "-m", "0644", str(BASE / "generated/daemon.json"), str(daemon)])
        run(["sudo", "apt-get", "install", "-y", "docker.io", "docker-compose-v2"])
        render()
        for conf in (BASE / "generated/configs").glob("**/*"):
            if conf.is_file():
                dest = DATA / "configs" / conf.relative_to(BASE / "generated/configs")
                run(["sudo", "mkdir", "-p", str(dest.parent)])
                exists = subprocess.run(["sudo", "test", "-e", str(dest)]).returncode == 0
                if not exists:
                    run(["sudo", "install", "-m", "0644", str(conf), str(dest)])
        preserve = "SETUP_USER,DATA_ROOT,HOMELAB_ROOT,DOCKER_ROOT,SAMBA_PASSWORD,ENABLE_BACKUPS,BORG_PASSPHRASE,BORG_REPO,SMART_DEVICE,ENABLE_SURICATA,DISABLE_SLEEP,ENABLE_STORAGE_SETUP,ENABLE_MONITORING,ENABLE_MUSIC,ENABLE_JELLYFIN,ENABLE_DESKTOP"
        run(["sudo", f"--preserve-env={preserve}", "bash", str(ROOT / "scripts/setup-host.sh")])
        run(["sudo", "systemctl", "enable", "--now", "docker", "smbd"])
        install_user_configs()
        if os.environ.get("ENABLE_UFW", "false").lower() == "true":
            ssh_port = os.environ.get("SSH_PORT", "22")
            run(["sudo", "ufw", "allow", f"{ssh_port}/tcp"])
            run(["sudo", "ufw", "allow", "in", "on", "tailscale0"])
            run(["sudo", "ufw", "default", "deny", "incoming"])
            run(["sudo", "ufw", "default", "allow", "outgoing"])
            run(["sudo", "ufw", "--force", "enable"])
        if os.environ.get("ENABLE_TAILSCALE", "false").lower() == "true":
            run(["bash", "-c", "curl -fsSL https://tailscale.com/install.sh | sh"])
            run(["sudo", "systemctl", "enable", "--now", "tailscaled"])
        if os.environ.get("ENABLE_DESKTOP", "false").lower() == "true":
            import pwd
            account = pwd.getpwnam(USER)
            run(["sudo", "env", f"TARGET_USER={USER}", f"TARGET_HOME={account.pw_dir}",
                 f"ENABLE_AUTOLOGIN={os.environ.get('ENABLE_AUTOLOGIN', 'false')}",
                 "bash", str(ROOT / "scripts/setup-desktop.sh")])
        return
    if action == "all":
        main("apply")
        main("start")
        return
    if action in ("start", "status"):
        if action == "start":
            validate_host_settings()
            render()
        compose = BASE / "generated/docker-compose.yml"
        if not compose.exists(): render()
        profiles = []
        for setting, profile in (("ENABLE_MONITORING", "monitoring"), ("ENABLE_MUSIC", "music"), ("ENABLE_JELLYFIN", "media")):
            if os.environ.get(setting, "true").lower() == "true": profiles.extend(["--profile", profile])
        base = ["sudo", "docker", "compose", *profiles, "-f", str(compose)]
        run(base + (["up", "-d"] if action == "start" else ["ps"]))
        if action == "start" and os.environ.get("ENABLE_VAULTWARDEN_TAILSCALE_SERVE", "false").lower() == "true":
            if not os.environ.get("TAILSCALE_DNS_NAME"):
                raise SystemExit("Set TAILSCALE_DNS_NAME before enabling Vaultwarden Tailscale Serve.")
            run(["sudo", "tailscale", "serve", "--bg", "2852"])
        if action == "start" and os.environ.get("ENABLE_SURICATA", "false").lower() == "true":
            if not IFACE:
                raise SystemExit("ENABLE_SURICATA requires NETWORK_INTERFACE to be set and reviewed.")
            run(["sudo", "docker", "compose", "-p", "sisyphus-suricata", "-f", str(BASE / "generated/suricata-compose.yml"), "up", "-d"])
        return
    raise SystemExit("Usage: setup.sh {render|apply|start|status|all}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "render")
