# Sisyphus

## Intro
Sisyphus is a security-first, homelab focused on blue-team detection, monitoring, and incident response, built on Ubuntu Server. The project is named so because of the number of times I had to start over everything while working on this.

The project focuses on:
- intrusion detection
- logging and SIEM
- network visibility
- secure remote access
- general homelab things

All the services currently run inside a security hardened single-node k3s cluster.

## Current Hardware
- HP Laptop
- Intel i5 (8th gen)
- 240GB SSD (OS)
- 1TB HDD (data)

## Setup
### 1. Ubuntu Server
- Refer [os-setup](./os-setup/README.md) for setting up the operating system.

### 2. Set up SSH server with firewall hardening
- Do this by yourself by finding the best ways to authenticate through SSH and connect it to the internet with atmost security. (this is of the most importance but cannot share it because of obvious reasons)

### 3. Disable sleep
```
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

### 4. Docker Installation and Setup

```
sudo apt install docker.io docker-compose
```

Add your user to the docker group:

```
sudo usermod -aG docker $USER
```

Move the docker storage to HDD (by default, it stores in `/var/lib/docker`)

```
sudo mkdir -p /etc/docker
sudo nano /etc/docker/daemon.json
```
Add
```
{
  "data-root": "/data/docker"
}
```
Restart docker
```
sudo systemctl restart docker
```
Reboot and verify

```
docker info | grep "Docker Root Dir"
```
should give
```
Docker Root Dir: /data/docker
```

### 5. Setting up directories
```
mkdir homelab
cd homelab
mkdir core storage monitoring security apps
cd /data 
sudo mkdir docker nas backups logs configs
sudo chown -R $USER:$USER /data
```

### 6. Homelab services
To set up homelab services, refer [homelab-services](./homelab-services/README.md)

### 7. Backups and misc
Now that we have a fully functioning homelab, we will go on to set up backups and cron jobs.


### 8. Other Tweaks
#### Connection
If the connection on SMB is slow,
```
sudo iw dev wlan0 set power_save off
```
In the file `/etc/samba/smb.conf`, add:
```
[global]
server min protocol = SMB2
socket options = TCP_NODELAY IPTOS_LOWDELAY
read raw = yes
write raw = yes
max xmit = 65535
```


# Comments while making the project
- 4th March 2026 - This project was supposed to be set up with kubernetes but after I learned the whole thing and installed k3s, the RAM usage went up to 2GB and my current infrastructure cannot support the whole working with kubernetes added to it. So yeah, sadly after wasting two days on it, I have to pivot away from it. 
