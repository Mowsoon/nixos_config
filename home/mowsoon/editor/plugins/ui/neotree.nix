{
  programs.nixvim.plugins.neo-tree = {
    enable = true;

    settings = {
      close_if_last_window = true;
      popup_border_style = "rounded";
      enable_git_status = true;
      enable_diagnostics = true;
      auto_clean_after_session_restore = true;

      window = {
        position = "left";
        width = 32;
        auto_expand_width = true;
        mappings = {
          "<space>" = "none";
          "l" = "none";
          "s" = "open_split";
          "v" = "open_vsplit";
          "c" = "copy_to_clipboard";
          "T" = "none";
          "U" = "none";
        };
      };

      filesystem = {
        bind_to_cwd = true;
        cwd_target.sidebar = "tab";
        hijack_netrw_behavior = "open_default";
        use_libuv_file_watcher = true;
        window.mappings = {
          "h" = "toggle_hidden";
          "H" = "none";
          "y" = "copy_path";
          "d" = "trash_now";
        };
        follow_current_file = {
          enabled = true;
          leave_dirs_open = false;
        };
        filtered_items = {
          visible = false;
          hide_dotfiles = false;
          hide_gitignored = true;
          never_show = [
            ".git"
            ".DS_Store"
            "thumbs.db"
            ".vscode"
            "node_modules"
            "__pycache__"
            ".ipynb_checkpoints"
          ];
        };
        commands = {
          copy_path.__raw = ''
            function(state)
              local node = state.tree:get_node()
              local filepath = node:get_id()
              vim.fn.setreg("+", filepath)
              print("Path copied to clipboard: " .. filepath)
            end
          '';
          trash_now.__raw = ''
            function(state)
              local inputs = require("neo-tree.ui.inputs")
              local confirm = inputs.confirm
              inputs.confirm = function(_, callback)
                callback(true)
              end
              local ok, err = pcall(require("neo-tree.sources.filesystem.commands").trash, state)
              inputs.confirm = confirm
              assert(ok, err)
            end
          '';
          trash_now_visual.__raw = ''
            function(state, selected_nodes)
              local inputs = require("neo-tree.ui.inputs")
              local confirm = inputs.confirm
              inputs.confirm = function(_, callback)
                callback(true)
              end
              local ok, err = pcall(
                require("neo-tree.sources.filesystem.commands").trash_visual,
                state,
                selected_nodes
              )
              inputs.confirm = confirm
              assert(ok, err)
            end
          '';
        };
      };

      source_selector = {
        winbar = true;
        statusline = false;
        sources = [
          {
            source = "filesystem";
            display_name = " Files";
          }
          {
            source = "buffers";
            display_name = " Buffers";
          }
          {
            source = "git_status";
            display_name = " Git";
          }
        ];
      };
    };
  };
}
