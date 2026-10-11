{
  programs.nixvim.plugins.gitsigns = {
    enable = true;

    settings = {
      signs = {
        add.text = "│";
        change.text = "│";
        delete.text = "_";
        topdelete.text = "‾";
        changedelete.text = "~";
      };

      current_line_blame = true;
      current_line_blame_opts = {
        delay = 400;
        virt_text_pos = "eol";
      };

      preview_config = {
        border = "rounded";
      };
    };
  };

  programs.nixvim.keymaps = [
    {
      mode = "n";
      key = "]c";
      action = ''<cmd>lua require("gitsigns").next_hunk()<CR>'';
      options = {
        silent = true;
        desc = "Next git hunk";
      };
    }
    {
      mode = "n";
      key = "[c";
      action = ''<cmd>lua require("gitsigns").prev_hunk()<CR>'';
      options = {
        silent = true;
        desc = "Previous git hunk";
      };
    }

    {
      mode = "n";
      key = "<leader>hp";
      action = ''<cmd>lua require("gitsigns").preview_hunk()<CR>'';
      options = {
        silent = true;
        desc = "Preview git hunk";
      };
    }
    {
      mode = "n";
      key = "<leader>hs";
      action = ''<cmd>lua require("gitsigns").stage_hunk()<CR>'';
      options = {
        silent = true;
        desc = "Stage git hunk";
      };
    }
    {
      mode = "n";
      key = "<leader>hr";
      action = ''<cmd>lua require("gitsigns").reset_hunk()<CR>'';
      options = {
        silent = true;
        desc = "Reset git hunk";
      };
    }
    {
      mode = "n";
      key = "<leader>gb";
      action = ''<cmd>lua require("gitsigns").blame_line()<CR>'';
      options = {
        silent = true;
        desc = "Full git blame popup";
      };
    }
  ];
}
