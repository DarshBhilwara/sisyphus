# VPN and Reverse Proxy Setup

## VPN Setup (TailScale)

### Installation
- Do the same steps for both client and server.
```
curl -fsSL https://tailscale.com/install.sh | sh
``` 
Enable
```
sudo systemctl enable --now tailscaled
```

### Run and set up 
```
sudo tailscale up --ssh
```

## Reverse Proxy Setup (traefik)
- `mkdir -p ~/homelab/proxy`
- `cd ~/homelab/proxy`
- Create the network `docker network create proxy`
- Create `docker-compose.yml` and add this
```
services:
  traefik:
    image: traefik:v3.7
    container_name: traefik
    restart: unless-stopped
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--log.level=INFO"
    ports:
      - "80:80"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - proxy
    labels:
      - traefik.enable=true
      - traefik.docker.network=proxy
      - traefik.http.routers.traefik.rule=Host(`traefik.home`)
      - traefik.http.routers.traefik.service=api@internal
networks:
  proxy:
    external: true
```
- Start it `docker-compose up -d`
- Next, go to `AdGuard->Filters->DNS Rewrites`
- Now add each of the services that you need to access from outside (`homarr`, `jellyfin`, `joplin`, `adguard`, `traefik`, `bookmarks`, `grafana`, `loki`, `dashdot`, `prometheus`) to the rewrite list like `service-name.home` in the domain and server's tailscale IP in the IP. 

