#!/bin/sh
# ThinkGRUB - remove the theme and regenerate grub.cfg
# Run:  pkexec ./uninstall.sh   (or: sudo ./uninstall.sh)
set -eu

DEST=${DEST:-/boot/grub/themes/thinkgrub}
GRUB_FILE=${GRUB_FILE:-/etc/default/grub}

[ "$(id -u)" -eq 0 ] || {
    echo "error: must run as root (sudo ./uninstall.sh or pkexec ./uninstall.sh)" >&2
    exit 1
}

sed -i 's|^GRUB_THEME=.*|GRUB_THEME=""|' "$GRUB_FILE"
update-grub
rm -rf "$DEST"

echo "Theme removed and grub.cfg regenerated."
echo "A backup of the original config is at $GRUB_FILE.bak"
