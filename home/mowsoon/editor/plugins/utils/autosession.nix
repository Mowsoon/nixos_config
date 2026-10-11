{
  programs.nixvim.plugins.auto-session = {
    enable = true;

    settings = {
      auto_save = true;
      auto_restore = true;
      auto_create = true;

      suppressed_dirs = [
        "~/"
        "~/Downloads"
        "~/Documents"
        "/tmp"
      ];

      bypass_save_filetypes = [
        "alpha"
        "neo-tree"
        "toggleterm"
      ];

      pre_save_cmds = [
        "Neotree close"
      ];

      session_lens = {
        load_on_setup = true;
      };
    };
  };

  programs.nixvim.keymaps = [
    {
      mode = "n";
      key = "<leader>ss";
      action = "<cmd>SessionSave<CR>";
      options = {
        silent = true;
        desc = "Save session";
      };
    }
    {
      mode = "n";
      key = "<leader>sr";
      action = "<cmd>SessionRestore<CR>";
      options = {
        silent = true;
        desc = "Restore session";
      };
    }
    {
      mode = "n";
      key = "<leader>sd";
      action = "<cmd>SessionDelete<CR>";
      options = {
        silent = true;
        desc = "Delete current session";
      };
    }
  ];
}
