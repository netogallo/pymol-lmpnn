def start_plugin():

    if check_installation():
        run_plugin()
        pass
    else:
        raise Exception("Additional components need to be installed before starting the plugin")

def ask_retry():
    return False

def is_already_installed():
    from os import path
    import os
    import re
    import subprocess
    from .constants import INSTALL_DIR
    
    install_dir = INSTALL_DIR
    pacman = path.join(install_dir, 'usr', 'bin', 'pacman.exe')
    check_re = r"Version\s+:\s+\d{8}-\d"

    try:
        p = subprocess.run(
            [pacman, '-Qi', 'mingw-w64-x86_64-python-lmpnn-gui'],
            capture_output = True, text = True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        output = str(p.stdout)

        if p.returncode == 0 and re.findall(check_re, output):
            # MySys2 is installed and lmpnn_gui is installed
            return True
        else:
            # MySys2 is installed but lmpnn_gui is not installed
            return False
    except Exception:
        return False

def check_installation_windows():
    from os import path
    from .installer import Installer

    if is_already_installed():
        return True

    current_dir = path.dirname(__file__)
    install_script = path.join(current_dir, "windows_install.py")

    return Installer(install_script).try_install()
    

def check_installation():
    import os

    if os.name == 'nt':
        return check_installation_windows()
        

    raise Exception(f"Your operating system '{os.name}' is not supported")

lmpnn_gui_process = None
def run_plugin():
    global lmpnn_gui_process
    from .LMPNNGuiProcess import LMPNNGuiProcess

    if lmpnn_gui_process is not None:
        lmpnn_gui_process.kill()
        lmpnn_gui_process.waitForFinished()

    lmpnn_gui_process = LMPNNGuiProcess()
    lmpnn_gui_process.start()


def __init_plugin__(app=None):
    from pymol.plugins import addmenuitemqt

    addmenuitemqt('LigandMPNN', start_plugin)
    check_installation()
