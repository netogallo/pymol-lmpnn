from os import path
import os

INSTALL_DIR = path.join(os.environ['LOCALAPPDATA'], 'pymol-lmpnn-gui')
MSYS_DIR = path.join(INSTALL_DIR, "msys64")
LMPNN_PYTHON = path.join(MSYS_DIR, "mingw64", "bin", "python")
PACMAN = path.join(MSYS_DIR, "usr", "bin", "pacman")
