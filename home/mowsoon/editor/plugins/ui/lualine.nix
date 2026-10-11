{
  programs.nixvim.plugins.lualine = {
    enable = true;

    settings = {
      options = {
        theme = "rose-pine";
        globalstatus = true;
        icons_enabled = false;

        component_separators = {
          left = "|";
          right = "|";
        };
        section_separators = {
          left = "|";
          right = "|";
        };
      };

      sections = {
        lualine_a = [ "mode" ];
        lualine_b = [
          "branch"
          "diff"
        ];
        lualine_c = [
          {
            __unkeyed-1 = "filename";
            path = 1;
            symbols = {
              modified = " [+] ";
              readonly = " [RO] ";
              unnamed = " [No Name] ";
            };
          }
        ];
        lualine_x = [
          {
            __unkeyed-1 = "diagnostics";
            sources = [ "nvim_lsp" ];
          }
          "filetype"
        ];
        lualine_y = [ "progress" ];
        lualine_z = [ "location" ];
      };
    };
  };
}
