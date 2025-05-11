from os import path
import os

INSTALL_DIR = path.join(os.environ['LOCALAPPDATA'], 'pymol-lmpnn-gui')
LMPNN_PYTHON = path.join(INSTALL_DIR, "mingw64", "bin", "python")
