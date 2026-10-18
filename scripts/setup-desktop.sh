#!/usr/bin/env bash
# Optional desktop/session setup, called by setup.sh after configuration validation.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Desktop setup requires root.' >&2; exit 1; }
: "${TARGET_USER:?Set TARGET_USER to a nonroot login user}"
[[ $(id -u "$TARGET_USER") != 0 ]] || { echo 'Choose a nonroot desktop user.' >&2; exit 1; }
TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
apt-get install -y xorg xinit openbox kitty x11-xserver-utils dbus-x11 ncurses-term \
    screenfetch btop tmux curl tar xz-utils fontconfig less pipewire-audio pipewire-pulse \
    pipewire-alsa wireplumber libspa-0.2-bluetooth bluez blueman alsa-utils \
    pulseaudio-utils util-linux wmctrl snapd
if ! command -v nvim >/dev/null; then snap install nvim --classic; fi
if ! command -v starship >/dev/null; then
    installer=$(mktemp)
    trap 'rm -f "$installer"' EXIT
    curl -fsSL https://starship.rs/install.sh -o "$installer"
    sh "$installer" -y
fi
if [[ $(dpkg --print-architecture) == amd64 ]]; then
    if ! command -v google-chrome-stable >/dev/null; then
        chrome_dir=$(mktemp -d)
        chmod 755 "$chrome_dir"
        curl -fL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o "$chrome_dir/chrome.deb"
        chmod 644 "$chrome_dir/chrome.deb"
        apt-get install -y "$chrome_dir/chrome.deb"
        rm -f "$chrome_dir/chrome.deb"
        rmdir "$chrome_dir"
    fi
else
    echo 'Chrome installation skipped: install a compatible browser and update chrome-session on this architecture.'
fi

# Match the documented on-demand Bluetooth/audio behavior.
systemctl mask --now bluetooth.service
systemctl_path=$(command -v systemctl)
sudoers=$(mktemp)
trap 'rm -f "$sudoers"' EXIT
printf '%s ALL=(root) NOPASSWD: %s unmask bluetooth.service, %s start bluetooth.service, %s stop bluetooth.service, %s mask bluetooth.service\n' \
    "$TARGET_USER" "$systemctl_path" "$systemctl_path" "$systemctl_path" "$systemctl_path" > "$sudoers"
visudo -cf "$sudoers"
install -m 0440 "$sudoers" /etc/sudoers.d/sisyphus-session-bluetooth
target_uid=$(id -u "$TARGET_USER")
runuser -u "$TARGET_USER" -- env HOME="$TARGET_HOME" XDG_RUNTIME_DIR="/run/user/$target_uid" \
    bash "$SCRIPT_DIR/desktop-user.sh"

# Console autologin is a separate explicit opt-in.
if [[ ${ENABLE_AUTOLOGIN:-false} == true ]]; then
    mkdir -p /etc/systemd/system/getty@tty1.service.d
    printf '[Service]\nExecStart=\nExecStart=-/sbin/agetty --autologin %s --noclear %%I linux\n' "$TARGET_USER" \
        > /etc/systemd/system/getty@tty1.service.d/sisyphus-autologin.conf
    systemctl daemon-reload
    systemctl enable getty@tty1.service
fi
