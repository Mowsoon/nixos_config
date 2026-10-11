{
  programs.nixvim.opts = {
    # Indent
    expandtab = true;
    shiftwidth = 2;
    tabstop = 2;
    softtabstop = 2;
    autoindent = true;
    smartindent = true;

    # UI
    number = true;
    relativenumber = true;
    cursorline = true;
    wrap = true;
    breakindent = true;
    linebreak = true;
    scrolloff = 10;
    sidescrolloff = 0;
    signcolumn = "yes";
    termguicolors = true;
    colorcolumn = "100";

    # Search
    ignorecase = true;
    smartcase = true;
    hlsearch = true;
    incsearch = true;
    inccommand = "nosplit";
    wrapscan = true;
    magic = true;

    # System & Files
    clipboard = "unnamedplus";
    mouse = "a";
    undofile = true;
    swapfile = false;
    updatetime = 250;
    timeoutlen = 300;
    confirm = true;
    autoread = true;
    backup = false;
    writebackup = false;

    # Splits
    splitbelow = false;
    splitright = true;

    # Folding
    foldenable = true;
    foldmethod = "expr";
    foldexpr = "v:lua.vim.treesitter.foldexpr()";
    foldlevel = 99;
    foldlevelstart = 99;
  };

  # Plugins
  programs.nixvim.globals = {
    loaded_gzip = 1;
    loaded_tar = 1;
    loaded_tarPlugin = 1;
    loaded_zip = 1;
    loaded_zipPlugin = 1;
    loaded_getscript = 1;
    loaded_getscriptPlugin = 1;
    loaded_vimball = 1;
    loaded_vimballPlugin = 1;
    loaded_matchit = 1;
    loaded_matchparen = 1;
    loaded_2html_plugin = 1;
    loaded_logiPat = 1;
    loaded_rrhelper = 1;
    loaded_netrw = 1;
    loaded_netrwPlugin = 1;
    loaded_netrwSettings = 1;
  };
}
