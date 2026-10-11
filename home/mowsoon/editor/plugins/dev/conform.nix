{ pkgs, ... }:

{
  programs.nixvim = {
    extraPackages = with pkgs; [
      nixfmt
      ruff
      gotools
      clang-tools
      shfmt
    ];

    plugins.conform-nvim = {
      enable = true;

      settings = {
        formatters_by_ft = {
          nix = [ "nixfmt" ];
          go = [
            "goimports"
            "gofmt"
          ];
          python = [ "ruff_format" ];
          c = [ "clang-format" ];
          cpp = [ "clang-format" ];
          bash = [ "shfmt" ];
          sh = [ "shfmt" ];
          "_" = [ "trim_whitespace" ];
        };

        format_on_save = {
          timeout_ms = 500;
          lsp_format = "fallback";
        };

        notify_on_error = true;
      };
    };

    keymaps = [
      {
        mode = "n";
        key = "<leader>cf";
        action = ''
          <cmd>lua require("conform").format({ async = true, lsp_format = "fallback" })<CR>
        '';
        options = {
          silent = true;
          desc = "Format buffer (Conform)";
        };
      }
    ];
  };
}
