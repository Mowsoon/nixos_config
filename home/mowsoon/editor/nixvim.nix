{

  imports = [
    ./cores
    ./plugins
  ];

  programs.nixvim = {
    enable = true;
    defaultEditor = true;
    nixpkgs.useGlobalPackages = true;

    globals = {
      mapleader = " ";
      maplocalleader = " ";
      loaded_ruby_provider = 0;
      loaded_perl_provider = 0;
    };

    clipboard = {
      register = "unnamedplus";
      providers.wl-copy.enable = true;
    };

  };
}
