{ pkgs, ... }:

{
  programs.nixvim.extraPackages = with pkgs; [
    ripgrep
    fd
  ];

  programs.nixvim.plugins.telescope = {
    enable = true;

    extensions.fzf-native.enable = true;

    lazyLoad.settings = {
      cmd = [ "Telescope" ];
      keys = [
        "<leader>ff"
        "<leader>fg"
        "<leader>fb"
        "<leader>fr"
        "<leader>fh"
      ];
    };

    keymaps = {
      "<leader>ff" = {
        action = "find_files";
        options.desc = "Find Files";
      };
      "<leader>fg" = {
        action = "live_grep";
        options.desc = "Live Grep";
      };
      "<leader>fb" = {
        action = "buffers";
        options.desc = "Find Open Buffers";
      };
      "<leader>fr" = {
        action = "oldfiles";
        options.desc = "Find Recently Opened Files";
      };
      "<leader>fh" = {
        action = "help_tags";
        options.desc = "Help";
      };
    };

    settings.defaults = {
      prompt_prefix = "> ";
      selection_caret = "> ";
      path_display = [ "truncate" ];

      file_ignore_patterns = [
        "^.git/"
        "^node_modules/"
        "^.terraform/"
        "%.lock"
      ];

      mappings = {
        i = {
          "<C-j>" = "move_selection_next";
          "<C-k>" = "move_selection_previous";
          "<C-q>" = "send_to_qflist";
          "<Esc>" = "close";
        };
      };
    };
  };
}
