{
  programs.nixvim.plugins.alpha = {
    enable = true;
    theme = null;

    lazyLoad.settings = {
      cmd = [
        "Alpha"
        "AlphaRedraw"
      ];
      keys = [
        {
          __unkeyed-1 = "<leader>a";
          __unkeyed-2 = "<cmd>Alpha<CR>";
          desc = "Dashboard";
        }
      ];
    };

    settings.layout = [
      {
        type = "padding";
        val = 4;
      }
      {
        type = "text";
        val = [
          "  _   _ _____ _____     _____ __  __ "
          " | \\ | | ____/ _ \\ \\   / /_ _|  \\/  |"
          " |  \\| |  _|| | | \\ \\ / / | || |\\/| |"
          " | |\\  | |__| |_| |\\ V /  | || |  | |"
          " |_| \\_|_____\\___/  \\_/  |___|_|  |_|"
        ];
        opts = {
          position = "center";
          hl = "Keyword";
        };
      }
      {
        type = "padding";
        val = 2;
      }
      {
        type = "group";
        val = [
          {
            type = "button";
            val = "  [f]  Find File";
            on_press.__raw = "function() require('telescope.builtin').find_files() end";
            opts = {
              keymap = [
                "n"
                "f"
                ":Telescope find_files<CR>"
                { silent = true; }
              ];
              position = "center";
              shortcut = "f";
              hl = "String";
              hl_shortcut = "Number";
            };
          }
          {
            type = "button";
            val = "  [r]  Recent Files";
            on_press.__raw = "function() require('telescope.builtin').oldfiles() end";
            opts = {
              keymap = [
                "n"
                "r"
                ":Telescope oldfiles<CR>"
                { silent = true; }
              ];
              position = "center";
              shortcut = "r";
              hl = "String";
              hl_shortcut = "Number";
            };
          }
          {
            type = "button";
            val = "  [g]  Live Grep";
            on_press.__raw = "function() require('telescope.builtin').live_grep() end";
            opts = {
              keymap = [
                "n"
                "g"
                ":Telescope live_grep<CR>"
                { silent = true; }
              ];
              position = "center";
              shortcut = "g";
              hl = "String";
              hl_shortcut = "Number";
            };
          }
          {
            type = "button";
            val = "  [e]  File Explorer";
            on_press.__raw = "function() vim.cmd('Neotree toggle') end";
            opts = {
              keymap = [
                "n"
                "e"
                ":Neotree toggle<CR>"
                { silent = true; }
              ];
              position = "center";
              shortcut = "e";
              hl = "String";
              hl_shortcut = "Number";
            };
          }
          {
            type = "button";
            val = "  [n]  New Buffer";
            on_press.__raw = "function() vim.cmd('enew') end";
            opts = {
              keymap = [
                "n"
                "n"
                ":enew<CR>"
                { silent = true; }
              ];
              position = "center";
              shortcut = "n";
              hl = "String";
              hl_shortcut = "Number";
            };
          }
          {
            type = "button";
            val = "  [q]  Quit";
            on_press.__raw = "function() vim.cmd('quit') end";
            opts = {
              keymap = [
                "n"
                "q"
                ":quit<CR>"
                { silent = true; }
              ];
              position = "center";
              shortcut = "q";
              hl = "String";
              hl_shortcut = "Number";
            };
          }
        ];
      }
      {
        type = "padding";
        val = 2;
      }
      {
        type = "text";
        val = "Workstation Neovim Environment";
        opts = {
          position = "center";
          hl = "Comment";
        };
      }
    ];
  };
}
