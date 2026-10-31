{
  programs.nixvim = {
    plugins.trouble = {
      enable = true;
    };

    keymaps = [
      {
        mode = "n";
        key = "<leader>xx";
        action = "<cmd>Trouble diagnostics toggle<CR>";
        options = {
          silent = true;
          desc = "Diagnostics (Trouble)";
        };
      }
      {
        mode = "n";
        key = "<leader>xb";
        action = "<cmd>Trouble diagnostics toggle filter.buf=0<CR>";
        options = {
          silent = true;
          desc = "Buffer Diagnostics (Trouble)";
        };
      }
      {
        mode = "n";
        key = "<leader>cs";
        action = "<cmd>Trouble symbols toggle focus=false<CR>";
        options = {
          silent = true;
          desc = "Symbols (Trouble)";
        };
      }
      {
        mode = "n";
        key = "<leader>cl";
        action = "<cmd>Trouble lsp toggle focus=false win.position=right<CR>";
        options = {
          silent = true;
          desc = "LSP Definitions / references / ... (Trouble)";
        };
      }
      {
        mode = "n";
        key = "<leader>xl";
        action = "<cmd>Trouble loclist toggle<CR>";
        options = {
          silent = true;
          desc = "Location List (Trouble)";
        };
      }
      {
        mode = "n";
        key = "<leader>xq";
        action = "<cmd>Trouble qflist toggle<CR>";
        options = {
          silent = true;
          desc = "Quickfix List (Trouble)";
        };
      }
    ];
  };
}
