{ pkgs
, qt5
, glib
, python3
, mkShell
, poetry
, gcc13
, stdenv
, libglvnd
, libkrb5
, makeWrapper
}:
let
  inherit (pkgs.lib) makeLibraryPath;
  pymol = pkgs.pymol.override {
    inherit qt5;
    python3Packages = python3.pkgs;
  };
  pythonLibs = makeLibraryPath [
    gcc13.cc
    gcc13.libc
    glib
    libglvnd
    libkrb5
  ];
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
        --prefix LD_LIBRARY_PATH : ${pythonLibs}
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
