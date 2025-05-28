from os import path
import os
import subprocess
import sys
import tempfile
from urllib.error import URLError
from urllib import request

INSTALL_DIR = path.join(os.environ['LOCALAPPDATA'], 'pymol-lmpnn-gui')
MSYS_DIR = path.join(INSTALL_DIR, "msys64")
PACMAN = path.join(MSYS_DIR, 'usr', 'bin', 'pacman.exe')
BASH = path.join(MSYS_DIR, 'usr', 'bin', 'bash.exe')
PLUGIN_DIR = path.dirname(__file__)
PKGS_DIR = path.join(PLUGIN_DIR, "pkgs")
UTILS_DIR = path.join(PLUGIN_DIR, "utils")
XZ = path.join(PLUGIN_DIR, "utils", "xz.exe")

class PacmanException(Exception):
    pass

def run_process(*args, cwd = None, env = None):
    subprocess.run(
        args,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check = True,
        stdout = sys.stdout,
        stderr = sys.stderr,
        cwd = cwd,
        env = env
    )

def bash(*args):
    cmd = [BASH] + list(args)
    run_process(*cmd)

def tar_windows(*args, cwd = None):
    cmd = ["tar"] + list(args)
    exe_path = os.pathsep.join([UTILS_DIR, os.environ["PATH"]])
    env = {
        **os.environ,
        'PATH': exe_path
    }
    run_process(*cmd, cwd = cwd, env = env)

def pacman(*args: str):

    cmd = [PACMAN] + list(args)

    try:
        run_process(*cmd)
    except Exception as e:
        raise PacmanException(e)

def xz(*args, cwd=None):
    cmd = [XZ] + list(args)
    run_process(*cmd, cwd=cwd)

def has_mysys2():

    try:
        pacman("--version")
        return True
    except FileNotFoundError:
        return False
    except PacmanException:
        return False

def download_mysys2(manual_ssl=False):
    msys2_installer = tempfile.mktemp(suffix=".tar.xz")
    msys2_url = "https://repo.msys2.org/distrib/msys2-x86_64-latest.tar.xz"

    run_process("curl", "-o", msys2_installer, msys2_url)
    return msys2_installer

def install_mysys2(remove_existing = False):
    import shutil

    if remove_existing and path.isdir(INSTALL_DIR):
        shutil.rmtree(INSTALL_DIR)

    if has_mysys2():
        return True

    try:
        msys2_installer = download_mysys2()
    except URLError:
        msys2_installer = download_mysys2(True)

    print(f"Installing into {INSTALL_DIR}")
    xz("-dv", msys2_installer)
    os.mkdir(INSTALL_DIR)
    msys2_tar = msys2_installer.replace(".xz","")
    tar_windows("-xvf", msys2_tar, "-C", INSTALL_DIR) 

    bash("--login", "-c", "pacman -Syu --noconfirm")

    return True

def install_pacman_pkgs():
    pkgs = [
        path.join(PKGS_DIR, file)
        for file in os.listdir(PKGS_DIR)
        if file.endswith(".tar.zst")
    ]

    pacman("-Syu", "--noconfirm")
    pacman("-U", "--noconfirm", *pkgs)


def install_all(remove_existing = False):

    install_mysys2(remove_existing)
    install_pacman_pkgs()

def main():
    try:
        install_all()
    except Exception as e:
        import time
        print(f"An error occured while upgrading. Trying a full re-install: {e}")
        print(f"Waiting 5 seconds so Windows doesn't freak out")
        time.sleep(5)
        install_all(True)

    print("Installation completed!")

if __name__ == '__main__':
    main()
