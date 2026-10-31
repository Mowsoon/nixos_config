{ pkgs, ... }:

{
  programs.nixvim = {
    extraPackages = with pkgs; [
      statix
      deadnix
      ruff
      shellcheck
      hadolint
      tflint
      golangci-lint
    ];

    plugins.lint = {
      enable = true;

      lintersByFt = {
        nix = [
          "statix"
          "deadnix"
        ];
        python = [ "ruff" ];
        bash = [ "shellcheck" ];
        sh = [ "shellcheck" ];
        dockerfile = [ "hadolint" ];
        terraform = [ "tflint" ];
        go = [ "golangci-lint" ];
      };

      autoCmd = {
        event = [
          "BufWritePost"
          "BufEnter"
        ];
      };
    };
  };
}
