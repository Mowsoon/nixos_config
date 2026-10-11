{
  programs.nixvim.keymaps = [
    # -------------------------------------------------------------
    # Clear search highlight (Esc)
    # -------------------------------------------------------------
    {
      mode = "n";
      key = "<Esc>";
      action = "<cmd>nohlsearch<CR>";
      options = {
        silent = true;
        desc = "Clear search highlight";
      };
    }
    # -------------------------------------------------------------
    # Next buffer (Tab)
    # -------------------------------------------------------------
    {
      mode = "n";
      key = "<Tab>";
      action = "<cmd>BufferLineCycleNext<CR>";
      options = {
        silent = true;
        desc = "Next buffer";
      };
    }
    # -------------------------------------------------------------
    # Previous buffer (Shift+Tab)
    # -------------------------------------------------------------
    {
      mode = "n";
      key = "<S-Tab>";
      action = "<cmd>BufferLineCyclePrev<CR>";
      options = {
        silent = true;
        desc = "Previous buffer";
      };
    }
    # -------------------------------------------------------------
    # Delete buffer (\bd)
    # -------------------------------------------------------------
    {
      mode = "n";
      key = "<leader>bd";
      action = "<cmd>bdelete<CR>";
      options = {
        silent = true;
        desc = "Delete buffer";
      };
    }
    # -------------------------------------------------------------
    # Toggle file explorer (\e)
    # -------------------------------------------------------------
    {
      mode = "n";
      key = "<leader>e";
      action = "<cmd>Neotree toggle<CR>";
      options = {
        silent = true;
        desc = "Toggle file explorer";
      };
    }
  ];
}
