# Operating System Setup - Ubuntu Server
This document describes the complete operating system installation and post-install configuration process for a clean Ubuntu Server setup with:

- SSD as main OS disk (LVM)
- HDD as separate LVM data volume mounted at `/data`
- Basic development + terminal tooling
- Clean console configuration
- Minimal, reproducible setup

---

# 1. Ubuntu Installation (Fresh Install)

Boot from Ubuntu Server ISO and follow these steps.

## Installation Steps

- Boot up **Ubuntu Server**
- Select language
- Set up keyboard layout
- Enable **third-party drivers**
- Connect to the internet
- Leave proxy address empty
- Use default mirrors
- Choose:
  - **Use entire SSD**
  - Set up as **LVM group**
- Set username, password, and server name
- Skip Ubuntu Pro
- Install **OpenSSH Server**
- Install all third-party drivers
- Do NOT choose any additional applications
- Start installation

After installation completes, reboot.

---

# 2. Configure Secondary HDD as LVM Data Volume

- Replace `<HDD>` with your actual device name (example: `sdb`).

Check using:

```
lsblk
```

---

## Wipe Existing Filesystem

```
sudo wipefs -a /dev/<HDD>
```

---

## Create LVM Structure

```
sudo pvcreate /dev/<HDD>
sudo vgcreate vgdata /dev/<HDD>
sudo lvcreate -l 100%FREE -n data vgdata
```

---

## Format and Mount

```
sudo mkfs.ext4 /dev/vgdata/data
sudo mkdir /data
sudo mount /dev/vgdata/data /data
```

Verify:

```
df -h
```

---

## Make Mount Persistent

Edit fstab:

```
sudo vim /etc/fstab
```

Add:

```
/dev/vgdata/data   /data   ext4   defaults,noatime   0   2
```

Test:

```
sudo mount -a
```

If no errors means the configuration is correct.

---

# 3. Install Base Packages

Install essential tools:

```
sudo apt update
sudo apt install neovim git ripgrep fd-find build-essential python3 nodejs npm screenfetch btop htop
```

---

# 4. Install Starship Prompt

Install:

```
curl -sS https://starship.rs/install.sh | sh
```

---

# 5. Console Font Configuration (TTY)

To improve readability:

```
sudo dpkg-reconfigure console-setup
```

Select:

- Character set: **Latin1 and Latin5**
- Font: **Terminus**
- Size: **16x32**

This gives large, clean console text.

---

# 6. Configure `.inputrc` (Better Shell History Navigation)

Edit:

```
vim ~/.inputrc
```

Add:

```
# Enable case-insensitive completion
set completion-ignore-case on

# Show all matches if ambiguous
set show-all-if-ambiguous on

# Enable colored completion (optional)
set colored-stats on

# History search with arrow keys
"\e[A": history-search-backward
"\e[B": history-search-forward
```

---

# 7. Clone Configuration Files

```
git clone https://github.com/DarshBhilwara/sisyphus.git
cd sisyphus/
cp -r .config ~/
```

---

# 8. Configure `.bashrc`

Edit:

```
vim ~/.bashrc
```

Add:

```
eval "$(starship init bash)"
screenfetch
```

Reboot

---

#  Final System Overview

You now have:

- Ubuntu Server on SSD (LVM)
- Separate HDD mounted at `/data`
- Persistent mount via fstab
- OpenSSH enabled
- Developer tools installed
- Starship prompt
- Improved TTY font
- Better shell history navigation
- Custom configuration loaded

