{
  programs.nixvim.plugins = {
    luasnip.enable = true;

    cmp = {
      enable = true;
      autoEnableSources = true;

      settings = {
        snippet = {
          expand = ''
            function(args)
                require("luasnip").lsp_expand(args.body)
            end
          '';
        };

        window = {
          completion = {
            border = "rounded";
            winhighlight = "Normal:Normal,FloatBorder:FloatBorder,CursorLine:Visual,Search:None";
          };
          documentation = {
            border = "rounded";
            winhighlight = "Normal:Normal,FloatBorder:FloatBorder,CursorLine:Visual,Search:None";
          };
        };

        sources = [
          { name = "nvim_lsp"; }
          { name = "luasnip"; }
          { name = "path"; }
          {
            name = "buffer";
            keyword_length = 3;
          }
        ];

        mapping = {
          "<C-Space>" = "cmp.mapping.complete()";
          "<C-e>" = "cmp.mapping.abort()";
          "<CR>" = "cmp.mapping.confirm({ select = false })";
          "<C-j>" = "cmp.mapping.select_next_item()";
          "<C-k>" = "cmp.mapping.select_prev_item()";
          "<C-b>" = "cmp.mapping.scroll_docs(-4)";
          "<C-f>" = "cmp.mapping.scroll_docs(4)";

          "<Tab>" = ''
            cmp.mapping(function(fallback)
            local luasnip = require('luasnip')
            if cmp.visible() then
                cmp.select_next_item()
            elseif luasnip.expand_or_jumpable() then
                luasnip.expand_or_jump()
            else
                fallback()
            end
            end, { "i", "s" })
          '';
          "<S-Tab>" = ''
            cmp.mapping(function(fallback)
            local luasnip = require('luasnip')
            if cmp.visible() then
                cmp.select_prev_item()
            elseif luasnip.jumpable(-1) then
                luasnip.jump(-1)
            else
                fallback()
            end
            end, { "i", "s" })
          '';
        };

        formatting = {
          fields = [
            "abbr"
            "kind"
            "menu"
          ];
          format = ''
            function(entry, vim_item)
                local menu_map = {
                    nvim_lsp = "[LSP]",
                    luasnip = "[Snip]",
                    buffer = "[Buf]",
                    path = "[Path]",
                }
                vim_item.menu = menu_map[entry.source.name] or string.format("[%s]", entry.source.name)
                return vim_item
            end
          '';
        };
      };
    };
  };
}
