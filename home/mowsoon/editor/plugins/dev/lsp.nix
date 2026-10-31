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
        };
      };
    };
  };

  programs.nixvim.diagnostic.settings = {
    virtual_text = true;
    severity_sort = true;
  };
}
