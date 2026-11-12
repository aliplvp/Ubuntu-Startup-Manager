#!/usr/bin/env bash
set -e
SCRIPT_DIR="${0%/*}"
[ "$SCRIPT_DIR" = "$0" ] && SCRIPT_DIR="."

APP_DIR="$HOME/.local/share/startup-manager"
BIN_DIR="$HOME/.local/bin"
AUTOSTART_DIR="$HOME/.config/autostart"
ICON_DIR="$HOME/.local/share/icons"
DESKTOP_DIR="$HOME/.local/share/applications"

mkdir -p "$APP_DIR" "$BIN_DIR" "$AUTOSTART_DIR" "$ICON_DIR" "$DESKTOP_DIR"
cp "${SCRIPT_DIR}/startup_manager.py" "$APP_DIR/startup_manager.py"
cp "${SCRIPT_DIR}/startup-manager.svg" "$ICON_DIR/startup-manager.svg"
chmod +x "$APP_DIR/startup_manager.py"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required."; exit 1
fi
if ! python3 -c 'import tkinter' >/dev/null 2>&1; then
  echo "Installing Tkinter..."
  sudo apt update
  sudo apt install -y python3-tk
fi

cat > "$BIN_DIR/startup-manager" <<EOF
#!/usr/bin/env bash
exec python3 "$APP_DIR/startup_manager.py" "\$@"
EOF
chmod +x "$BIN_DIR/startup-manager"

cat > "$DESKTOP_DIR/startup-manager.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Startup Manager
Comment=Manage applications that start automatically
Exec=$BIN_DIR/startup-manager
Icon=$ICON_DIR/startup-manager.svg
Terminal=false
Categories=Settings;System;
StartupNotify=true
EOF
chmod +x "$DESKTOP_DIR/startup-manager.desktop"

# Add app launcher to the desktop when the Desktop folder exists.
if [ -d "$HOME/Desktop" ]; then
  cp "$DESKTOP_DIR/startup-manager.desktop" "$HOME/Desktop/Startup Manager.desktop"
  chmod +x "$HOME/Desktop/Startup Manager.desktop"
  gio set "$HOME/Desktop/Startup Manager.desktop" metadata::trusted true 2>/dev/null || true
fi

echo
echo "Startup Manager installed."
echo "Open it from the Applications menu by searching: Startup Manager"
echo "Or run: startup-manager"
