{
  description = "A very basic flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-24.05";
    #pymol = {
    #  type = "github";
    #  owner = "schrodinger";
    #  repo = "pymol-open-source";
    #  flake = false;
    #};
    utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, utils }:
    let
      inherit (utils.lib) eachDefaultSystem;
      flake = system:
        let
          pkgs = import nixpkgs { inherit system; };
          python3 = pkgs.python3;
          qt5 = pkgs.qt5;
          pymol = pkgs.pymol.override {
            inherit qt5;
            python3Packages = python3.pkgs;
          };
        in
          {
            devShells = {
              default = pkgs.mkShell {
                name = "pymol";
                packages = [
                  pymol
                  python3.pkgs.ipython
                  python3
                  pkgs.poetry
                  python3.pkgs.virtualenv

                  # Easy way to make qt work with ipython
                  python3.pkgs.pyqt5
                  python3.pkgs.pyqt5-stubs
                ];
              };
            };
          }
      ;
    in
      eachDefaultSystem flake
  ;
}
