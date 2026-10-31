{ lib, ... }:

{
  programs.nixvim = {
    plugins.bufferline = {
      enable = true;

      settings = {
        options = {
          mode = "buffers";
          always_show_bufferline = true;
          separator_style = "thin";
          numbers = "ordinal";

          show_buffer_icons = false;
          show_buffer_close_icons = false;
          show_close_icon = false;
          close_command.__raw = "function(buffer) require('mini.bufremove').delete(buffer, false) end";
          right_mouse_command.__raw = "function(buffer) require('mini.bufremove').delete(buffer, false) end";

          truncate_names = true;
          max_name_length = 25;
          sort_by = "directory";

          enforce_regular_tabs = false;
          indicator = {
            style = "underline";
          };

          diagnostics = "nvim_lsp";
          diagnostics_indicator = ''
            function(count, level, diagnostics_dict, context)
                local s = " "
                for e, n in pairs(diagnostics_dict) do
                    local sym = e == "error" and "[E]"
                        or (e == "warning" and "[W]" or "[I]")
                    s = s .. n .. sym
                end
                return s
            end
          '';

          offsets = [
            {
              filetype = "neo-tree";
              text = "EXPLORER";
              text_align = "center";
              separator = true;
            }
          ];
        };
      };
    };

    keymaps =
      lib.imap1
        (index: key: {
          mode = "n";
          key = "<M-${key}>";
          action = "<cmd>BufferLineGoToBuffer ${toString index}<CR>";
          options = {
            silent = true;
            desc = "Go to buffer ${toString index}";
          };
        })
        [
          "&"
          "é"
          "\""
          "'"
          "("
          "-"
          "è"
          "_"
          "ç"
        ];
  };
}
