{
  programs.nixvim.colorschemes.rose-pine = {
    enable = true;

    settings = {
      variant = "main";
      darkvariant = "main";
      dim_inactive_windows = true;
      extend_background_behind_borders = true;

      disable_background = false;
      disable_float_background = false;

      styles = {
        bold = true;
        italic = false;
        transparency = false;
      };

      highlight_groups = {
        FloatBorder = {
          fg = "muted";
          bg = "surface";
        };
      };
    };
  };
}
