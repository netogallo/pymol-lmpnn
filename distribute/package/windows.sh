#!/usr/bin/bash

set -e

# Install makepkg
dir=$1
cd "$dir"
pacman -S --noconfirm --needed base-devel zip wget

export MINGW_PACKAGE_PREFIX="mingw-w64-x86_64"
export MINGW_PREFIX="/mingw64"
export MSYSTEM="mingw-w64"
export LMPNN_GUI_VERSION="$(date +%Y%m%d)"
export LMPNN_GUI_RELEASE="1"

# Build the lmpnn_gui package
tar -czvf "$dir/distribute/lmpnn_gui/lmpnn_gui.src.tar.gz" "lmpnn_gui"

cd "$dir/distribute/lmpnn_gui"
makepkg -sf --noconfirm
cd "$dir"

# Create the pymol plugin
PKGNAME="$MINGW_PACKAGE_PREFIX-python-lmpnn-gui-$LMPNN_GUI_VERSION-$LMPNN_GUI_RELEASE-any.pkg.tar.zst"
mv "$dir/distribute/lmpnn_gui/$PKGNAME" "$dir/lmpnn_gui_pymol/pkgs"

# Download xz and bundle with the plugin
mkdir -p "$dir/lmpnn_gui_pymol/utils"
XZ_TMP=$(mktemp -d)
XZ_TOOLS="$XZ_TMP/xz-5.8.1-windows.zip"
XZ_TOOLS_OUT="$XZ_TMP"
wget -O "$XZ_TOOLS" "https://github.com/tukaani-project/xz/releases/download/v5.8.1/xz-5.8.1-windows.zip"
(cd "$XZ_TMP" && unzip "$XZ_TOOLS")
mv $XZ_TOOLS_OUT/bin_x86-64/* "$dir/lmpnn_gui_pymol/utils/"

zip -r "lmpnn-gui-pymol-$LMPNN_GUI_VERSION-w64.zip" "lmpnn_gui_pymol"
