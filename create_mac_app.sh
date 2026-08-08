#!/bin/bash
# Create native macOS App bundle for CI-Hörtrainer

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

APP_NAME="CI-Hörtrainer.app"
CONTENTS_DIR="$APP_NAME/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

# Create Info.plist
cat << 'EOF' > "$CONTENTS_DIR/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>CI-Hörtrainer</string>
    <key>CFBundleIdentifier</key>
    <string>de.ci-hoertrainer.app</string>
    <key>CFBundleName</key>
    <string>CI-Hörtrainer</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
</dict>
</plist>
EOF

# Create executable launcher binary
cat << 'EOF' > "$MACOS_DIR/CI-Hörtrainer"
#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../../.." >/dev/null 2>&1 && pwd )"
cd "$DIR"
/usr/bin/python3 "$DIR/main.py"
EOF

chmod +x "$MACOS_DIR/CI-Hörtrainer"
echo "🚀 Native macOS Anwendung '$APP_NAME' wurde erfolgreich erstellt!"
