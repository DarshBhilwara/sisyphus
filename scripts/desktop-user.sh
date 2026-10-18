#!/usr/bin/env bash
# Run only through setup-desktop.sh as the target user.
set -euo pipefail
umask 077
mkdir -p "$HOME/.local/bin" "$HOME/.config"
# Preserve prior settings before installing the documented desktop configuration.
backup_dir="$HOME/.local/state/sisyphus-desktop/$(date +%Y%m%d-%H%M%S)-$$"
for relative in .xinitrc .bash_profile .tmux.conf .inputrc .config/kitty/kitty.conf .config/openbox/autostart .config/openbox/rc.xml .local/bin/btt .local/bin/chrome-session .local/bin/close-chrome-session .local/bin/audio-key; do
    if [[ -e "$HOME/$relative" ]]; then
        mkdir -p "$backup_dir/$(dirname "$relative")"
        cp -a "$HOME/$relative" "$backup_dir/$relative"
    fi
done
mkdir -p ~/.config/kitty

cat > ~/.config/kitty/kitty.conf <<'EOF'
# Font
font_family      DroidSansM Nerd Font
bold_font        auto
italic_font      auto
bold_italic_font auto
font_size        12.0

# Kanagawa Wave
background              #1F1F28
foreground              #DCD7BA
selection_background    #2D4F67
selection_foreground    #C8C093
cursor                  #C8C093
url_color               #72A7BC

# Normal colors
color0  #16161D
color1  #C34043
color2  #76946A
color3  #C0A36E
color4  #7E9CD8
color5  #957FB8
color6  #6A9589
color7  #C8C093

# Bright colors
color8  #727169
color9  #E82424
color10 #98BB6C
color11 #E6C384
color12 #7FB4CA
color13 #938AA9
color14 #7AA89F
color15 #DCD7BA

# Scrollback
scrollback_lines 20000
wheel_scroll_multiplier 5.0
scrollback_pager less --chop-long-lines --RAW-CONTROL-CHARS +INPUT_LINE_NUMBER

# Window appearance
hide_window_decorations no
background_opacity 1.0
cursor_shape block
cursor_blink_interval 0
enable_audio_bell no
confirm_os_window_close 0
remember_window_size no

# Terminal scrollback shortcuts
map ctrl+shift+up scroll_line_up
map ctrl+shift+down scroll_line_down
map ctrl+shift+home scroll_home
map ctrl+shift+end scroll_end
EOF

cat > ~/.tmux.conf <<'EOF'
# Prefix
set -g prefix C-b
unbind C-b
bind C-b send-prefix

# Mouse support
set -g mouse on

# History
set -g history-limit 50000

# Colors
set -g default-terminal "tmux-256color"
set -ga terminal-overrides ",*:Tc"

# Numbering
set -g base-index 1
setw -g pane-base-index 1
set -g renumber-windows on

# Responsiveness
set -sg escape-time 10
set -g focus-events on
set -g allow-rename off

# Kanagawa-inspired status bar
set -g status-position bottom
set -g status-interval 5
set -g status-style "bg=#1F1F28,fg=#DCD7BA"
set -g message-style "bg=#2D4F67,fg=#DCD7BA"
set -g pane-border-style "fg=#54546D"
set -g pane-active-border-style "fg=#7E9CD8"

set -g status-left-length 30
set -g status-right-length 60
set -g status-left "#[fg=#1F1F28,bg=#76946A,bold] #S #[default] "
set -g status-right "#[fg=#7E9CD8] %H:%M #[fg=#C0A36E]| #[fg=#DCD7BA] %d-%b-%Y "

setw -g window-status-format " #I:#W "
setw -g window-status-current-format "#[fg=#1F1F28,bg=#7E9CD8,bold] #I:#W #[default]"

# Vi-style copy mode
setw -g mode-keys vi
bind-key -T copy-mode-vi v send-keys -X begin-selection
bind-key -T copy-mode-vi y send-keys -X copy-selection-and-cancel

# Reload this configuration using prefix + r
bind r source-file ~/.tmux.conf \; display-message "tmux config reloaded"
EOF

cat > ~/.xinitrc <<'EOF'
#!/bin/sh
exec openbox-session
EOF

chmod +x ~/.xinitrc

mkdir -p ~/.config/openbox

if [ ! -f ~/.config/openbox/rc.xml ]; then
    cp /etc/xdg/openbox/rc.xml ~/.config/openbox/rc.xml
fi

cat > ~/.config/openbox/autostart <<'EOF'
#!/bin/sh

# Prevent screen blanking and power management
xset s off
xset -dpms
xset s noblank

# Terminal + tmux + btop
kitty --start-as=maximized tmux new-session -A -s monitor btop &
EOF

chmod +x ~/.config/openbox/autostart

touch ~/.bash_profile

if ! grep -q 'AUTO_OPENBOX_TTY1' ~/.bash_profile; then
  cat >> ~/.bash_profile <<'EOF'

# AUTO_OPENBOX_TTY1
if [ -z "$DISPLAY" ] &&
   [ "$(tty 2>/dev/null)" = "/dev/tty1" ]; then
    exec startx
fi
EOF
fi

if ! grep -q 'LOAD_BASHRC_FOR_LOGIN_SHELLS' ~/.bash_profile; then
  cat >> ~/.bash_profile <<'EOF'

# LOAD_BASHRC_FOR_LOGIN_SHELLS
if [[ -f "$HOME/.bashrc" ]]; then
    source "$HOME/.bashrc"
fi
EOF
fi


mkdir -p ~/.local/bin

cat > ~/.local/bin/btt <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

SYSTEMCTL="$(command -v systemctl)"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-$HOME/.cache}"
mkdir -p "$RUNTIME_DIR"
exec 9>"$RUNTIME_DIR/btt.lock"
flock -x 9

AUDIO_UNITS=(
    pipewire.service
    pipewire.socket
    pipewire-pulse.service
    pipewire-pulse.socket
    wireplumber.service
)

case "${1:-}" in
    start)
        systemctl --user unmask "${AUDIO_UNITS[@]}"
        systemctl --user start \
            pipewire.socket \
            pipewire-pulse.socket \
            pipewire.service \
            pipewire-pulse.service \
            wireplumber.service
        sudo -n "$SYSTEMCTL" unmask bluetooth.service
        sudo -n "$SYSTEMCTL" start bluetooth.service
        # Give BlueZ time to initialize before starting Blueman.
        sleep 5
        blueman-applet 9>&- >/dev/null 2>&1 &
        # Let the applet connect before opening the manager.
        sleep 5
        blueman-manager 9>&- >/dev/null 2>&1 &
        ;;
    end)
        pkill -TERM -x blueman-manager 2>/dev/null || true
        pkill -TERM -x blueman-applet 2>/dev/null || true
        sudo -n "$SYSTEMCTL" stop bluetooth.service
        sudo -n "$SYSTEMCTL" mask bluetooth.service
        systemctl --user stop \
            wireplumber.service \
            pipewire-pulse.service \
            pipewire-pulse.socket \
            pipewire.service \
            pipewire.socket
        systemctl --user mask "${AUDIO_UNITS[@]}"
        ;;
    *)
        echo "Usage: btt {start|end}" >&2
        exit 2
        ;;
esac
EOF

chmod +x ~/.local/bin/btt

mkdir -p ~/.local/bin ~/.local/share

cat > ~/.local/bin/chrome-session <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

PROFILE="$HOME/.local/share/chrome-openbox-profile"

exec google-chrome-stable \
    --user-data-dir="$PROFILE" \
    --no-first-run \
    --disable-background-mode \
    "$@"
EOF

chmod +x ~/.local/bin/chrome-session

cat > ~/.local/bin/close-chrome-session <<'EOF'
#!/usr/bin/env bash

PROFILE="$HOME/.local/share/chrome-openbox-profile"

for pid in $(pgrep -x chrome || true); do
    [[ -r "/proc/$pid/cmdline" ]] || continue

    cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"

    # Only close the main process belonging to our dedicated profile.
    [[ "$cmdline" == *"--user-data-dir=$PROFILE"* ]] || continue
    [[ "$cmdline" == *"--type="* ]] && continue

    kill -TERM "$pid" 2>/dev/null || true
done
EOF

chmod +x ~/.local/bin/close-chrome-session

cat > ~/.local/bin/audio-key <<'EOF'
#!/usr/bin/env bash

case "${1:-}" in
    up)
        wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 5%+
        ;;
    down)
        wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-
        ;;
    mute)
        wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle
        ;;
    mic)
        wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle
        ;;
    *)
        exit 2
        ;;
esac >/dev/null 2>&1 || true
EOF

chmod +x ~/.local/bin/audio-key

python3 - <<'PY'
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

home = Path.home()
config = home / ".config/openbox/rc.xml"
config.parent.mkdir(parents=True, exist_ok=True)

if not config.exists():
    shutil.copy("/etc/xdg/openbox/rc.xml", config)

tree = ET.parse(config)
root = tree.getroot()

namespace = ""
if root.tag.startswith("{"):
    namespace = root.tag[1:].split("}", 1)[0]
    ET.register_namespace("", namespace)

def tag(name):
    return f"{{{namespace}}}{name}" if namespace else name

keyboard = root.find(tag("keyboard"))
if keyboard is None:
    keyboard = ET.SubElement(root, tag("keyboard"))

bin_dir = home / ".local/bin"

bindings = {
    "W-f": str(bin_dir / "chrome-session"),
    "W-Escape": str(bin_dir / "close-chrome-session"),
    "W-b": f"{bin_dir}/btt start",
    "W-S-b": f"{bin_dir}/btt end",
    "XF86AudioRaiseVolume": f"{bin_dir}/audio-key up",
    "XF86AudioLowerVolume": f"{bin_dir}/audio-key down",
    "XF86AudioMute": f"{bin_dir}/audio-key mute",
    "XF86AudioMicMute": f"{bin_dir}/audio-key mic",
}

for item in list(keyboard.findall(tag("keybind"))):
    if item.get("key") in bindings:
        keyboard.remove(item)

for key, command in bindings.items():
    keybind = ET.SubElement(keyboard, tag("keybind"), {"key": key})
    action = ET.SubElement(keybind, tag("action"), {"name": "Execute"})
    ET.SubElement(action, tag("command")).text = command

ET.indent(tree, space="  ")
tree.write(config, encoding="UTF-8", xml_declaration=True)
print(f"Updated {config}")
PY



cat > "$HOME/.inputrc" <<'EOF'
set completion-ignore-case on
set show-all-if-ambiguous on
set colored-stats on
"\e[A": history-search-backward
"\e[B": history-search-forward
EOF
if ! grep -q 'SISYPHUS_SHELL' "$HOME/.bashrc" 2>/dev/null; then
    cat >> "$HOME/.bashrc" <<'EOF'
# SISYPHUS_SHELL
export PATH="$HOME/.local/bin:$PATH"
command -v starship >/dev/null && eval "$(starship init bash)"
command -v screenfetch >/dev/null && screenfetch
EOF
fi
font_dir="$HOME/.local/share/fonts/DroidSansMonoNerdFont"
if [[ ! -f "$font_dir/.sisyphus-installed" ]]; then
    mkdir -p "$font_dir"
    archive=$(mktemp)
    trap 'rm -f "$archive"' EXIT
    curl -fL https://github.com/ryanoasis/nerd-fonts/releases/latest/download/DroidSansMono.tar.xz -o "$archive"
    tar -xf "$archive" -C "$font_dir"
    fc-cache -f
    touch "$font_dir/.sisyphus-installed"
fi
# The user service manager may not exist until this user logs in.
if systemctl --user show-environment >/dev/null 2>&1; then
    systemctl --user mask --now pipewire.service pipewire.socket pipewire-pulse.service pipewire-pulse.socket wireplumber.service
else
    mkdir -p "$HOME/.config/systemd/user"
    for unit in pipewire.service pipewire.socket pipewire-pulse.service pipewire-pulse.socket wireplumber.service; do
        ln -sfn /dev/null "$HOME/.config/systemd/user/$unit"
    done
fi
printf 'Desktop files installed; prior files saved in %s when present. Log in on tty1 to start Openbox.\n' "$backup_dir"
