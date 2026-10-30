{
  programs.nixvim.colorschemes.catppuccin = {
    enable = true;

    settings = {
      flavour = "mocha";
      no_italic = true;
      no_bold = false;

      dim_inactive = {
        enabled = true;
        shade = "dark";
        percentage = 0.15;
      };

      color_overrides.mocha = {
        base = "#1c1626";
        mantle = "#17121f";
        crust = "#120e18";
        surface0 = "#2b2338";
        surface1 = "#3a3049";
        surface2 = "#4a3f5b";
        overlay0 = "#5f5470";
        overlay1 = "#73688a";
        overlay2 = "#887d9f";
        subtext0 = "#a89fbc";
        subtext1 = "#bdb4cf";
        text = "#d9d2e6";
      };

      integrations = {
        fidget = true;
        lsp_trouble = true;
        which_key = true;
      };

      custom_highlights.__raw = ''
        function(colors)
          return {
            FloatBorder = { fg = colors.overlay1, bg = colors.mantle },
          }
        end
      '';
    };
  };
}
