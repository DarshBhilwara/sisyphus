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



# Comments while making the project
- 4th March 226 - This project was supposed to be set up with kubernetes but after I learned the whole thing and installed k3s, the RAM usage went up to 2GB and my current infrastructure cannot support the whole working with kubernetes added to it. So yeah, sadly after wasting two days on it, I have to pivot away from it. 