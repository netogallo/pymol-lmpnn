{ pkgs
, qt5
, python3
, mkShell
}:
let
  pymol = pkgs.pymol.override {
    inherit qt5;
    python3Packages = python3.pkgs;
  };
  lmpnn-gui-python = python3.withPackages (
    p: with p;
    [ ipython
      pyqt6
      pyqt6-sip

      # For linting the code running
      # on pymol
      pyqt5
      pyqt5-sip
      pyqt5-stubs
      debugpy
      rdkit
      virtualenv
      scipy
      pymol
      pytest
    ])
  ;
in
{
  default = mkShell {
    name = "pymol";
    packages = [
      pymol
      lmpnn-gui-python
    ];
    shellHook = ''
      SITE_PACKAGES="${lmpnn-gui-python}/lib/python3.12/site-packages"
      VENV="$PWD/.venv"
      CUSTOM_PATH="$VENV/lib/python3.12/site-packages/custom_path.pth"
      mk_venv() {
        rm -rf "$VENV"
        virtualenv --system-site-packages "$VENV"

        # For some reason, python forgets to add all packages
        echo "$SITE_PACKAGES"  > "$CUSTOM_PATH"
      }

      check_venv() {

        if [ ! -f "$CUSTOM_PATH" ]; then
          echo "Warning! The python virtual environment at '.venv' was not created using 'mk_venv'. Trust you know hat you are doing :)"
          return
        fi

        SITE_PACKAGES_CURRENT=$(cat $CUSTOM_PATH)

        if [ "$SITE_PACKAGES" != "$SITE_PACKAGES_CURRENT" ]; then
          echo "Warning! The python interpreter is different from the one in your virtual environment. It is recommended to re-build the environment by running 'mk_venv'"
        fi
      }

      if [ -d "$VENV" ]; then
        check_venv
      fi
    '';
  };
}
