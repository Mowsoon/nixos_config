{
  programs.nixvim.plugins.toggleterm = {
    enable = true;

    settings = {
      size = ''
        function(term)
          if term.direction == "horizontal" then
            return 15
          elseif term.direction == "vertical" then
            return vim.o.columns * 0.4
          end
        end
      '';

      open_mapping = "[[<C-\\>]]";
      hide_numbers = true;
      shade_terminals = false;
      start_in_insert = true;
      persist_size = true;
      direction = "float";
      close_on_exit = true;
      auto_scroll = true;

      float_opts = {
        border = "rounded";
        winblend = 0;
      };
    };
  };

  programs.nixvim.keymaps = [
    {
      mode = [
        "n"
        "t"
      ];
      key = "<leader>tf";
      action = "<cmd>ToggleTerm direction=float<CR>";
      options = {
        silent = true;
        desc = "Toggle terminal (float)";
      };
    }
    {
      mode = [
        "n"
        "t"
      ];
      key = "<leader>th";
      action = "<cmd>ToggleTerm size=15 direction=horizontal<CR>";
      options = {
        silent = true;
        desc = "Toggle terminal (horizontal split)";
      };
    }
  ];
}
