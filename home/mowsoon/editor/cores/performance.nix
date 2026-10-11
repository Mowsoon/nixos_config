{
  programs.nixvim.performance = {
    byteCompileLua = {
      enable = true;
      configs = true;
      plugins = true;
    };

    combinePlugins = {
      enable = true;
      standalonePlugins = [ ];
    };
  };
}
