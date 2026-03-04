# 1. Dashboard
We will use `Homepage` for dashboards.

```
mkdir -p /data/configs/homepage
cd ~/homelab/apps
mkdir dashboard
cd dashboard
vim docker-compose.yaml
```

Include config like
```
services:
 homepage:
  image: ghcr.io/gethomepage/homepage:latest
  container_name: homepage
  ports:
   - 3000:3000
  volumes:
   - /data/configs/homepage:/app/config 
   - /var/run/docker.sock:/var/run/docker.sock:ro 
  environment:
   HOMEPAGE_ALLOWED_HOSTS: "*"
  restart: unless-stopped
```
Run
```
docker-compose up -d 
```

# 2. NAS
We will use `samba` for SMB
```
sudo apt install samba
```
Create share
```
sudo vim /etc/samba/smb.conf
```
Add this at the very bottom:
```
[nas]
   path = /data/nas
   browseable = yes
   read only = no
   guest ok = no
   valid users = $USER
   create mask = 0664
   directory mask = 0775
```
Create a new password for SMB
```
sudo smbpasswd -a $USER
```
Set permissions
```
sudo chown -R $USER:$USER /data/nas                                            
chmod 775 /data/nas
```

Restart SMB
```
sudo systemctl restart smbd
```

Connect to it with
```
smb://server-ip/nas
```

# 3. Phone Backup
We will use `syncthing`

```
mkdir -p /data/configs/syncthing
mkdir -p /data/nas/phone-backup
sudo chown -R 1000:1000 /data/configs/syncthing
sudo chmod -R 755 /data/configs/syncthing
cd ~/homelab/apps
mkdir syncthing
cd syncthing
vim docker-compose.yml
```
Insert this:
```
services:
  syncthing:
    image: syncthing/syncthing:latest
    container_name: syncthing
    ports:
      - "8384:8384"
      - "22000:22000/tcp"
      - "22000:22000/udp"
    volumes:
      - /data/configs/syncthing:/var/syncthing/config
      - /data/nas/phone-backup:/var/syncthing/phone
    restart: unless-stopped
```
Run
```
docker-compose up -d 
```
Now set up and use `syncthing`

# 4. Notes with sync
# 5. Bookmarks with sync
# 6. Streaming 
# 7. Cron Jobs
