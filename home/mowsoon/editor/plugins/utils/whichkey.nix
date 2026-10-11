{
  programs.nixvim.plugins.which-key = {
    enable = true;

    settings = {
      delay = 300;
      preset = "modern";

      win = {
        border = "rounded";
        padding = [
          1
          2
        ];
        title = true;
      };

      spec = [
        {
          __unkeyed-1 = "<leader>b";
          group = "Buffers";
        }
        {
          __unkeyed-1 = "<leader>c";
          group = "Code / LSP";
        }
        {
          __unkeyed-1 = "<leader>f";
          group = "Find (Telescope)";
        }
        {
          __unkeyed-1 = "<leader>g";
          group = "Git (Fugitive)";
        }
        {
          __unkeyed-1 = "<leader>h";
          group = "Git Hunks (Gitsigns)";
        }
        {
          __unkeyed-1 = "<leader>x";
          group = "Diagnostics (Trouble)";
        }
      ];
    };
  };
}
