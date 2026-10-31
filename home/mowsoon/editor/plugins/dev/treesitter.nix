{ lib, pkgs, ... }:

{
  programs.nixvim = {
    globals = {
      no_python_maps = 1;
      no_go_maps = 1;
      no_rust_maps = 1;
    };

    plugins = {
      treesitter = {
        enable = true;

        grammarPackages = with pkgs.vimPlugins.nvim-treesitter.builtGrammars; [
          bash
          c
          cpp
          go
          gomod
          gosum
          python
          yaml
          json
          nix
          terraform
          markdown
          markdown_inline
          lua
          make
        ];

        settings = {
          highlight = {
            enable = true;
            additional_vim_regex_highlighting = false;
          };

          indent = {
            enable = true;
          };
        };

        nixvimInjections = true;
      };

      treesitter-context = {
        enable = true;

        settings = {
          max_lines = 3;
          min_window_height = 20;
          line_numbers = true;
          mode = "cursor";
        };
      };

      treesitter-textobjects = {
        enable = true;

        settings = {
          select.lookahead = true;
          move.set_jumps = true;
        };
      };
    };

    keymaps =
      lib.mapAttrsToList
        (key: target: {
          mode = [
            "x"
            "o"
          ];
          inherit key;
          action.__raw = ''
            function()
              require("nvim-treesitter-textobjects.select").select_textobject("${target.query}", "textobjects")
            end
          '';
          options.desc = target.desc;
        })
        {
          "af" = {
            query = "@function.outer";
            desc = "Around function";
          };
          "if" = {
            query = "@function.inner";
            desc = "Inside function";
          };
          "ac" = {
            query = "@class.outer";
            desc = "Around class";
          };
          "ic" = {
            query = "@class.inner";
            desc = "Inside class";
          };
          "aa" = {
            query = "@parameter.outer";
            desc = "Around parameter";
          };
          "ia" = {
            query = "@parameter.inner";
            desc = "Inside parameter";
          };
        }
      ++
        lib.mapAttrsToList
          (key: target: {
            mode = [
              "n"
              "x"
              "o"
            ];
            inherit key;
            action.__raw = ''
              function()
                require("nvim-treesitter-textobjects.move").${target.move}("${target.query}", "textobjects")
              end
            '';
            options.desc = target.desc;
          })
          {
            "]m" = {
              move = "goto_next_start";
              query = "@function.outer";
              desc = "Next function";
            };
            "[m" = {
              move = "goto_previous_start";
              query = "@function.outer";
              desc = "Previous function";
            };
            "]]" = {
              move = "goto_next_start";
              query = "@class.outer";
              desc = "Next class";
            };
            "[[" = {
              move = "goto_previous_start";
              query = "@class.outer";
              desc = "Previous class";
            };
          };
  };
}
