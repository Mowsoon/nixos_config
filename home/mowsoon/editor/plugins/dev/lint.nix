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

    keymaps = [
      {
        mode = "n";
        key = "<leader>cl";
        action = ''<cmd>lua require("lint").try_lint()<CR>'';
        options = {
          silent = true;
          desc = "Trigger linter (nvim-lint)";
        };
      }
    ];
  };
}
