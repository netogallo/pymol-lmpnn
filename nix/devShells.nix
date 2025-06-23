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
      debugpy
      virtualenv
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
      mk-venv() {
        virtualenv --system-site-packages .venv

        # For some reason, python forgets to add all packages
        echo "$SITE_PACKAGES"  > .venv/lib/python3.12/site-packages/custom_path.pth
      }

      if [ -d "$PWD/.venv" ]; then
        echo "$SITE_PACKAGES"  > .venv/lib/python3.12/site-packages/custom_path.pth
      fi
    '';
  };
}
