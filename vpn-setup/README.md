# VPN Setup (TailScale)


## Installation
- Do the same steps for both client and server.
```
curl -fsSL https://tailscale.com/install.sh | sh
``` 
Enable
```
sudo systemctl enable --now tailscaled
```

## Run and set up 
```
sudo tailscale up --ssh
```
