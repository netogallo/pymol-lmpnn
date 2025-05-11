from os import path
import os
import ssl
import subprocess
import sys
import tempfile
from urllib.error import URLError
from urllib import request

INSTALL_DIR = path.join(os.environ['LOCALAPPDATA'], 'pymol-lmpnn-gui')
PACMAN = path.join(INSTALL_DIR, 'usr', 'bin', 'pacman.exe')
PLUGIN_DIR = path.dirname(__file__)
PKGS_DIR = path.join(PLUGIN_DIR, "pkgs")
MYSYS2_CA = path.join(PLUGIN_DIR, "mysys2.crt")

class PacmanException(Exception):
    pass

def run_process(*args):
    subprocess.run(
        args,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check = True,
        stdout = sys.stdout,
        stderr = sys.stderr
    )

def pacman(*args: str):

    cmd = [PACMAN] + list(args)

    try:
        run_process(*cmd)
    except Exception as e:
        raise PacmanException(e)

def has_mysys2():

    try:
        pacman("--version")
        return True
    except FileNotFoundError:
        return False
    except PacmanException:
        return False

def download_mysys2(manual_ssl=False):
    mysys2_installer = tempfile.mktemp(suffix=".exe")
    mysys2_url = "https://repo.msys2.org/distrib/msys2-x86_64-latest.exe"

    if manual_ssl:
        # Python, is it too much to ask to be able to do https
        # requests w/o having to install additional packages?

        ssl_ctx = ssl.create_default_context(cafile=MYSYS2_CA)
        response = request.urlopen(mysys2_url, context=ssl_ctx)
    else:
        response = request.urlopen(mysys2_url)

    approx_size = 82*1024*1024
    count = 0
    perc = 0
    print(f"Saving mysys2 installer to {mysys2_installer}")
    with open(mysys2_installer, 'wb') as fs, response:
        while True:
            bs = response.read(8192)

            if len(bs) == 0:
                return mysys2_installer

            count += len(bs)
            new_perc = int(100 * min(1,count / approx_size))
            if new_perc > perc:
                perc = new_perc
                print(f"Downloading mysys2 {perc}%")
            fs.write(bs)

def install_mysys2(remove_existing = False):

    if remove_existing and path.isdir(INSTALL_DIR):
        os.removedirs(INSTALL_DIR)

    if has_mysys2():
        return True

    try:
        mysys2_installer = download_mysys2()
    except URLError:
        mysys2_installer = download_mysys2(True)

    print(f"Installing into {INSTALL_DIR}")

    run_process(mysys2_installer, "in", "--confirm-command", "--accept-messages", "--root", INSTALL_DIR)

    pacman("-Syu", "--noconfirm")

    return True

def install_pacman_pkgs():
    pkgs = [
        path.join(PKGS_DIR, file)
        for file in os.listdir(PKGS_DIR)
        if file.endswith(".tar.zst")
    ]

    pacman("-U", "--noconfirm", *pkgs)


def install_all(remove_existing = False):

    install_mysys2(remove_existing)
    install_pacman_pkgs()

def main():
    try:
        install_all()
    except Exception as e:
        print(f"An error occured while upgrading. Trying a full re-install: {e}")
        install_all(True)

    print("Installation completed!")

if __name__ == '__main__':
    main()
