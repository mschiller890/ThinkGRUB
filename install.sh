#!/bin/sh
# ThinkGRUB - minimal black & white GRUB theme
# Install:  pkexec ./install.sh   (or: sudo ./install.sh)
set -eu

SRC=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DEST=${DEST:-/boot/grub/themes/thinkgrub}
GRUB_FILE=${GRUB_FILE:-/etc/default/grub}
TIMEOUT=${TIMEOUT:-5}

[ "$(id -u)" -eq 0 ] || {
    echo "error: must run as root (sudo ./install.sh or pkexec ./install.sh)" >&2
    exit 1
}

echo "[1/4] Installing theme to $DEST"
rm -rf "$DEST"
mkdir -p "$DEST"
cp "$SRC/theme.txt" "$SRC/panel.png" "$SRC/logo.png" "$DEST/"
cp "$SRC"/sel_*.png "$SRC"/item_*.png "$SRC"/terminal_box_*.png "$DEST/"
cp "$SRC"/DejaVuSans-*.pf2 "$DEST/"

echo "[2/4] Backing up $GRUB_FILE"
[ -f "$GRUB_FILE.bak" ] || cp "$GRUB_FILE" "$GRUB_FILE.bak"

echo "[3/4] Configuring GRUB"
if grep -q '^GRUB_THEME=' "$GRUB_FILE"; then
    sed -i "s|^GRUB_THEME=.*|GRUB_THEME=\"$DEST/theme.txt\"|" "$GRUB_FILE"
else
    printf 'GRUB_THEME="%s/theme.txt"\n' "$DEST" >> "$GRUB_FILE"
fi
sed -i "s/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=$TIMEOUT/" "$GRUB_FILE"
sed -i 's/^GRUB_TIMEOUT_STYLE=.*/GRUB_TIMEOUT_STYLE=menu/' "$GRUB_FILE"

echo "[4/4] Regenerating grub.cfg"
update-grub

echo
echo "Done. GRUB now uses:"
grep -E 'GRUB_THEME|GRUB_TIMEOUT' "$GRUB_FILE"
