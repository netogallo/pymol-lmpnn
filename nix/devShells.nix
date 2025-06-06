{ pkgs, qt5, python3, mkShell, poetry, gcc13, stdenv, makeWrapper }:
let
  pymol = pkgs.pymol.override {
    inherit qt5;
    python3Packages = python3.pkgs;
  };
  poetry-wrapped = stdenv.mkDerivation {
    pname = "wrapped-poetry";
    version = "1.0.0";

    # Poetry binary and wrapper tool
    buildInputs = [
      poetry
      makeWrapper
    ];

    # No actual unpack/build needed
    dontUnpack = true;
    dontBuild = true;

    installPhase = ''
      mkdir -p $out/bin

      # Wrap poetry
      makeWrapper ${pkgs.poetry}/bin/poetry $out/bin/poetry \
        --set POETRY_HOME /my/custom/poetry/home \
        --prefix LD_LIBRARY_PATH : ${gcc13.cc.lib}/lib
    '';
  };
in
{
  default = mkShell {
    name = "pymol";
    nativeBuildInputs = [ pkgs.makeWrapper ];
    packages = [
      pymol
      poetry-wrapped
      python3
      python3.pkgs.virtualenv

      # Easy way to make qt work with ipython
      python3.pkgs.pyqt5
      python3.pkgs.pyqt5-stubs
    ];
    shellHook = ''
      # export SHELL=/run/current-system/sw/bin/bash
      # LD_LIBRARY_PATH="${pkgs.gcc13.cc.lib}/lib/"
    '';
  };
}
