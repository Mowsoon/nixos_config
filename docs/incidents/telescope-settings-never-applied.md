# Telescope settings never applied

## Overview

On 2026-10-31, the search for file names ignored hidden files although the configuration asked
Telescope to show them. Inside Neovim, `require("telescope.config").values.file_ignore_patterns`
was `nil` and the per-picker settings were empty: none of the declared Telescope settings had ever
been applied, including the key mappings of the search window and the fzf sorter.

Affected configuration:

| Component | Version |
| --- | --- |
| NixVim | `performance.combinePlugins` on, Telescope lazy-loaded through lz.n on its keys and command |
| Telescope | With the `telescope-fzf-native` extension |

Cause: lz.n creates a stub `:Telescope` command and calls `require("telescope").setup()` only when
the stub or one of the declared keys first runs. In nixpkgs, `telescope-fzf-native` depends on
`telescope.nvim`; the extension is loaded at start, so Telescope itself landed in the combined
start package. Its `plugin/telescope.lua` is sourced after `init.lua` and replaced the stub with the
real command, and the key mappings of NixVim, defined after the triggers of lz.n, replaced those
too. Nothing ever called the setup, and Telescope ran on its defaults.

Resolution: `home/mowsoon/editor/plugins/ui/telescope.nix` no longer lazy-loads Telescope, so its
setup runs at start. Telescope was already loaded at start through the extension, so this costs
nothing.

## How to verify the fix

1. In Neovim, print the ignore patterns. The command must print the list declared in
   `telescope.nix`, not `nil`.

   ```vim
   :lua print(vim.inspect(require("telescope.config").values.file_ignore_patterns))
   ```

2. In a repository with a tracked hidden file, `<leader>ff` must list it.

## Reference

| Source | Content |
| --- | --- |
| [lz.n](https://github.com/nvim-neorocks/lz.n) | Triggers of the lazy loader |
| [NixVim performance options](https://nix-community.github.io/nixvim/performance/index.html) | `combinePlugins` and the combined start package |
