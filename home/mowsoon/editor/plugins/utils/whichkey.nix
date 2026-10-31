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
          group = "Git";
        }
        {
          __unkeyed-1 = "<leader>h";
          group = "Git Hunks (Gitsigns)";
        }
        {
          __unkeyed-1 = "<leader>s";
          group = "Sessions";
        }
        {
          __unkeyed-1 = "<leader>t";
          group = "Terminal";
        }
        {
          __unkeyed-1 = "<leader>x";
          group = "Diagnostics (Trouble)";
        }
      ];
    };
  };
}
