{
  programs.nixvim.plugins.fugitive = {
    enable = true;
  };

  programs.nixvim.keymaps = [
    {
      mode = "n";
      key = "<leader>gs";
      action = "<cmd>Git<CR>";
      options = {
        silent = true;
        desc = "Git status dashboard (Fugitive)";
      };
    }
    {
      mode = "n";
      key = "<leader>gd";
      action = "<cmd>Gdiffsplit<CR>";
      options = {
        silent = true;
        desc = "Git diff split";
      };
    }
    {
      mode = "n";
      key = "<leader>gc";
      action = "<cmd>Git commit<CR>";
      options = {
        silent = true;
        desc = "Git commit";
      };
    }
    {
      mode = "n";
      key = "<leader>gp";
      action = "<cmd>Git push<CR>";
      options = {
        silent = true;
        desc = "Git push";
      };
    }
    {
      mode = "n";
      key = "<leader>gl";
      action = "<cmd>Git log --oneline<CR>";
      options = {
        silent = true;
        desc = "Git log (oneline)";
      };
    }
  ];
}
