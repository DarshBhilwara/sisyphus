# Recreate this setup on a new Ubuntu host

This bootstrap targets a fresh Ubuntu Server 26.04+ host. Rendering is read-only with respect to host settings and `/data`; `apply` installs packages and sets up the host, and `all` applies then starts enabled services. Disk provisioning is a separate explicit opt-in and can erase the selected disk. The scripts never modify SSH policy or migrate existing Docker data. Do not use `apply` on the current system when you only intend to inspect a generated config.

## Prepare

Start with a fresh supported Ubuntu Server install and a normal sudo-enabled account. `scripts/setup.sh hardware` prints read-only hardware inventory and suggested settings. The documented manual OS flow creates `/data`; alternatively, set `ENABLE_STORAGE_SETUP=true`, an explicit `/dev/disk/by-id/...` `DATA_DISK`, and `ALLOW_DISK_ERASE=true` to opt into separate LVM/ext4 disk provisioning. Review the selected device carefully; storage setup is destructive and must be disabled after the one-time setup. Clone this repository, copy `setup.env.example` to the ignored `setup.env`, and set `SETUP_USER`, `HOMELAB_ROOT`, `LAN_IP`, interface, and strong unique secrets. Set `LAN_IP` to the server's fixed LAN address; published admin interfaces bind there. Keep the example values out of real deployments. `HOMARR_SECRET_ENCRYPTION_KEY` must be 64 hex characters. Do not share `setup.env`.

`REQUIRE_DATA_MOUNT=true` prevents writing the stack onto the OS disk when the data volume is missing. Set it to `false` deliberately for a system without a separate data disk.

## Render, inspect, apply

On the new Ubuntu host, install Git if needed (`sudo apt update` then `sudo apt install -y git`), clone this repository, and enter its folder. Run these commands as your normal sudo-enabled login user:

```sh
scripts/setup.sh hardware
cp setup.env.example setup.env
chmod 600 setup.env
${EDITOR:-nano} setup.env
scripts/setup.sh render
scripts/setup.sh all
scripts/setup.sh status
```

`setup.env` uses Bash assignments. Single-quote passwords containing `$`, spaces, or shell punctuation. Generate the Homarr key with `openssl rand -hex 32` and keep it for later runs. Use different passwords for each service. Changing a database password in the env file after initialization does not change the stored database password. `JOPLIN_BASE_URL` must match the URL you use to access Joplin (default `http://joplin.home`).

Render initializes a staged tree and writes compose files under `$HOMELAB_ROOT/generated`; it does not create `/data` files or install packages. Existing `/data/configs` are preserved during apply. Compose contains secrets and is mode 0600. Inspect it before use. `scripts/setup.sh apply` installs packages, configures Docker's fresh `data-root` at `/data/docker`, Samba, cron maintenance, and optional backups/desktop/tuning; run it as the configured non-root account with sudo. It refuses a detected conflicting Docker `data-root`; resolve that by hand before applying. `scripts/setup.sh start` and `status` manage enabled Compose profiles; `scripts/setup.sh all` applies then starts. `SETUP_ENV_FILE=/path/to/private.env` selects another environment file. `ENABLE_MONITORING`, `ENABLE_MUSIC`, and `ENABLE_JELLYFIN` select service profiles; hardware acceleration is opt-in with `JELLYFIN_HW_ACCEL=true` and requires `/dev/dri`.

The main stack covers Traefik, current Homarr, Syncthing, Joplin/Postgres, Bookmarksman, Jellyfin, Dashdot, Vaultwarden, Navidrome/Beets, AdGuard Home, Grafana, Loki, Prometheus, Alloy, node-exporter, cAdvisor, and AdGuard exporter. Suricata has a separate rendered compose file and starts only after you provide the correct interface and review its capture permissions. Alloy tails system, Docker, and Suricata logs; Promtail's prior configuration remains generated for compatibility. Promtail reached end of life on 2026-03-02, so use Alloy for fresh deployments. Homarr uses the official [Docker installation](https://homarr.dev/docs/getting-started/installation/docker/) layout and `/appdata`.

Bookmarksman runs entirely in Docker (`darshbhilwara/bookmarksman:1.0.0`), with persistent data in `$DATA_ROOT/configs/bookmarksman` and access at `http://LAN_IP:1024` or `http://bookmarksman.home` after DNS setup. Apply creates its data directory as UID/GID 999 with mode 0750; no host Python packages or application service are installed. Existing static bookmark files are left untouched and are not automatically imported.

## Host and application steps that remain manual

- Samba's share is added through a separate managed include; set `SAMBA_PASSWORD` in the private environment and apply the host stage to provision the account. Never reuse your login password.
- Set up Tailscale login, DNS rewrites, router DHCP/DNS, and remote access in the Tailscale admin console. Do not expose admin ports on a public interface.
- AdGuard publishes TCP/UDP port 53 on `LAN_IP`; use a fixed LAN address to avoid Ubuntu resolver conflicts on loopback. Router DHCP/DNS and Tailscale DNS changes remain manual.
- Create Joplin, Syncthing, Jellyfin, and Vaultwarden accounts and finish their onboarding. Set up Vaultwarden's admin token and TLS/`tailscale serve` only after deciding your access model.
- During AdGuard's first-run setup, create the account matching `ADGUARD_USERNAME` and `ADGUARD_PASSWORD`; use LAN port 3000 for the wizard, and port 3003 after configuring the UI on its normal port 80. The generated Traefik route and exporter target the final internal port 80; they become available after onboarding.
- Configure Suricata's interface and rules and import your Grafana dashboards (the original guide lists IDs 1860, 20799, and 14282). Grafana data sources are provisioned automatically. Existing app configs are never overwritten. Promtail is deprecated; see [Grafana's notice](https://grafana.com/docs/loki/latest/send-data/promtail/).
- Set `ENABLE_BACKUPS=true` and a strong `BORG_PASSPHRASE` to initialize Borg and install the opt-in cron schedule. Backups require sufficient separate storage and a tested restore procedure. Replication installs no existing application state, credentials, datasets, device pairing, router settings, or backup contents.
- Optional desktop, UFW, Tailscale installation, and Tailscale Serve are opt-in through environment settings; review each host change before enabling it. UFW/firewall policy and desktop autologin are not enabled by default.

Set `ENABLE_DESKTOP=true` to install the optional Openbox/Kitty/tmux/Chrome session, Starship, fonts, Bluetooth/audio helpers, and key bindings. `ENABLE_AUTOLOGIN=true` opts into the tty1 autologin unit. The installer backs up files it replaces. Font console reconfiguration remains interactive, Chrome is only installed on supported amd64 systems, and key bindings may need adaptation for different hardware. Apply copies missing repository `.config` files into the target account while excluding runtime logs. Set `ENABLE_VAULTWARDEN_TAILSCALE_SERVE=true` with a logged-in Tailscale client, set `TAILSCALE_DNS_NAME` to its full tailnet DNS name, and configure `VAULTWARDEN_DOMAIN=https://<device-name>.<tailnet>.ts.net` to serve Vaultwarden privately. Set `ENABLE_UFW=true` only after verifying `SSH_PORT` and your recovery access. UFW does not filter Docker-published ports by default; restrict exposure with the bind address and upstream firewall. `DISABLE_SLEEP=true` applies the documented sleep and lid behavior.

The original OS guide includes destructive disk commands. The optional disk setup is separate and requires both explicit device selection and erase approval; review `scripts/setup-storage.sh` before enabling it.

## Hardware choices

| Setting | Purpose |
| --- | --- |
| `ENABLE_MONITORING` | Grafana, Prometheus, Loki, Alloy, and exporters |
| `ENABLE_MUSIC` | Navidrome and Beets |
| `ENABLE_JELLYFIN` | Media streaming |
| `JELLYFIN_HW_ACCEL` | Expose `/dev/dri`; select the matching acceleration mode in Jellyfin afterward |
| `ENABLE_SURICATA` | Packet capture on the explicit `NETWORK_INTERFACE` |
| `ENABLE_DESKTOP` / `ENABLE_AUTOLOGIN` | Desktop and separate unattended console login |
| `DISABLE_SLEEP` | Keep a laptop running with its lid closed; reboot to apply lid settings |
| `SMART_DEVICE` | Optional block device for periodic SMART checks |

For a small machine, begin with monitoring, desktop, and Suricata disabled, then enable what fits your workload. Images track upstream tags; this reproduces configuration rather than guaranteeing identical future image releases. Pin image digests in the generated Compose file for a fixed release set.

## Backups

`ENABLE_BACKUPS=true` initializes Borg at `BORG_REPO` (default `$DATA_ROOT/backups/borg`) and schedules daily 03:00 backups with seven daily, four weekly, and six monthly archives. Use a mounted separate disk to protect against data-disk failure; the default same-disk repository cannot provide that protection.

Backups briefly stop currently running containers in the main stack, copy `/home`, `/etc`, and data configs/logs/NAS directories, then restart those containers even if Borg fails. Docker images can be downloaded again and are excluded. Schedule downtime accordingly. Maintenance logs go to the journal; backup output goes to `/var/log/sisyphus-backup.log`. Keep the Borg passphrase and an exported repository key off the server, and test a restore before depending on the schedule.
