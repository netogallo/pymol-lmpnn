{
  description = "A very basic flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-24.05";
    utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, utils }:
    let
      inherit (utils.lib) eachDefaultSystem;
      flake = system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
          {
            devShells = pkgs.callPackage ./nix/devShells.nix {};
          }
      ;
    in
      eachDefaultSystem flake
  ;
}
