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

# 4. Notes 
We will use `joplin` for notes
```
sudo mkdir -p /data/configs/joplin/postgres
sudo chown -R 999:999 /data/configs/joplin/postgres
cd ~/homelab/apps
mkdir joplin
cd joplin
vim docker-compose.yml
```
Insert this:
```
services:
  db:
    image: postgres:16
    container_name: joplin-db
    restart: unless-stopped
    volumes:
      - /data/configs/joplin/postgres:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: joplin
      POSTGRES_PASSWORD: password
      POSTGRES_DB: joplindb

  app:
    image: joplin/server:latest
    container_name: joplin-server
    restart: unless-stopped
    depends_on:
      - db
    ports:
      - "22300:22300"
    environment:
      APP_PORT: 22300
      APP_BASE_URL: http://server-ip:22300
      DB_CLIENT: pg
      POSTGRES_HOST: db
      POSTGRES_PORT: 5432
      POSTGRES_USER: joplin
      POSTGRES_PASSWORD: password
      POSTGRES_DATABASE: joplindb
```
Run by 
```
docker-compose up -d
```

Visit `http://server-ip:22300` from client and set up joplin
- Login - `admin@localhost`
- Password - `admin`

# 5. Bookmarks 
We will use `linkding` for this
```
sudo mkdir -p /data/configs/linkding
sudo chown -R $USER:$USER /data/configs/linkding
mkdir -p ~/homelab/apps/linkding
cd ~/homelab/apps/linkding
vim docker-compose.yml
```
Insert this
```
services:
  linkding:
    image: sissbruecker/linkding:latest
    container_name: linkding
    ports:
      - "9090:9090"
    volumes:
      - /data/configs/linkding:/etc/linkding/data
    restart: unless-stopped
```
Then start
```
docker-compose up -d
```
Visit `http://server-ip:9090` on the client and set up your bookmarks
- Login - `admin`
- Password - `admin`

# 6. Streaming 
We will use `jellyfin` for this
```
mkdir -p /data/nas/media/movies
mkdir -p /data/nas/media/tv
mkdir -p /data/nas/media/personal
mkdir -p /data/configs/jellyfin
mkdir -p /data/configs/jellyfin/cache
cd ~/homelab/apps
mkdir jellyfin
cd jellyfin
vim docker-compose.yml
```
Insert this:
```
services:
  jellyfin:
    image: jellyfin/jellyfin:latest
    container_name: jellyfin
    ports:
      - "8096:8096"
    volumes:
      - /data/configs/jellyfin:/config
      - /data/configs/jellyfin/cache:/cache
      - /data/nas:/nas
    devices:
      - /dev/dri:/dev/dri
    restart: unless-stopped
```
Then start
```
docker-compose up -d
```
Visit `http://server-ip:8096` on the client and set up your account