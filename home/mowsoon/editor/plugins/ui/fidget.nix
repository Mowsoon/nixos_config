{
  programs.nixvim.plugins.fidget = {
    enable = true;
    settings = {
      progress = {
        display = {
          done_icon = "✔";
        };
      };
      notification = {
        window = {
          winblend = 0;
        };
      };
    };
  };
}
