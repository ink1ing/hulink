#!/bin/bash
# 构建 macOS 程序：dist/Hulink.app + Hulink.dmg + Hulink.pkg
set -e
cd "$(dirname "$0")/.."

[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt pyinstaller

# 1) 打包为 .app
pyinstaller --noconfirm --clean --windowed --name Hulink gui.py

# 2) DMG（hdiutil 为 macOS 自带）
hdiutil create -volname Hulink -srcfolder "dist/Hulink.app" -ov -format UDZO "dist/Hulink.dmg"

# 3) PKG 安装包（pkgbuild 为 macOS 自带，安装到 /Applications）
pkgbuild --install-location /Applications --component "dist/Hulink.app" "dist/Hulink.pkg"

echo "构建完成: dist/Hulink.app, dist/Hulink.dmg, dist/Hulink.pkg"
echo "提示: 未签名，分发时 Gatekeeper 会拦截；正式发布需 codesign + notarytool。"
