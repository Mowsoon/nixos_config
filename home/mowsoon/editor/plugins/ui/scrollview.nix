{
  programs.nixvim = {
    plugins.scrollview = {
      enable = true;
      settings = {
        excluded_filetypes = [
          "neo-tree"
          "alpha"
        ];
      };
    };
    extraConfigLua = ''
      require("scrollview.contrib.gitsigns").setup()
    '';
  };
}
