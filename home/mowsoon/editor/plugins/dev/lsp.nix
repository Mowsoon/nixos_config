{
  programs.nixvim.plugins = {
    schemastore = {
      enable = true;
      yaml.enable = true;
      json.enable = true;
    };

    lsp = {
      enable = true;
      inlayHints = true;

      servers = {
        nil_ls.enable = true;
        gopls.enable = true;
        bashls.enable = true;
        clangd.enable = true;
        rust_analyzer = {
          enable = true;
          installCargo = false;
          installRustc = false;
        };
        pyright.enable = true;
        ts_ls.enable = true;
        jsonls.enable = true;
        yamlls.enable = true;
        helm_ls.enable = true;
        html.enable = true;
        cssls.enable = true;
        lua_ls.enable = true;
        terraformls.enable = true;
      };

      keymaps = {
        silent = true;
        lspBuf = {
          "gd" = "definition";
          "gD" = "declaration";
          "gi" = "implementation";
          "gr" = "references";
          "K" = "hover";
          "<leader>rn" = "rename";
          "<leader>ca" = "code_action";
          "<leader>f" = "format";
        };
        diagnostic = {
          "[d" = "goto_prev";
          "]d" = "goto_next";
          "<leader>d" = "open_float";
        };
      };
    };
  };
}
