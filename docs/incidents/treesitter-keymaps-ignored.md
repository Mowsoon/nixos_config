# Treesitter key mappings ignored

## Overview

On 2026-10-31, none of the Treesitter key mappings declared for the editor worked: `Enter` did not
start a selection, the text objects `af`, `if`, `ac`, `ic`, `aa` and `ia` did not exist, and
`]m`, `[m`, `]]` and `[[` moved only in Python files, through the Python file type plugin of Vim.
Highlighting, indentation and folding worked.

Affected configuration:

| Component | Version |
| --- | --- |
| Neovim | 0.12 |
| nvim-treesitter, nvim-treesitter-textobjects | `main` branch, as packaged in nixpkgs |

Cause: the `main` branch of nvim-treesitter dropped its module system, `incremental_selection`
included, and the `main` branch of nvim-treesitter-textobjects no longer creates key mappings from
its settings: it only exposes functions to call from mappings. The declared settings were accepted
and ignored. The file type plugins of Python, Go and Rust also map `]]`, `[[`, `]m` and `[m` to the
buffer, which takes precedence over a global mapping.

Resolution: `home/mowsoon/editor/plugins/dev/treesitter.nix` declares the text objects and moves as
key mappings that call the functions of nvim-treesitter-textobjects, and sets `no_python_maps`,
`no_go_maps` and `no_rust_maps` so that the file type plugins leave these keys free. Incremental
selection uses the native `an` and `in` of Neovim 0.12 instead of `Enter` and `Backspace`.

## How to verify the fix

1. Open a Python file, put the cursor inside a method and type `vaf`. The whole method must be
   selected.
2. Put the cursor in a function defined after a class and type `[[`. The cursor must move to the
   line of the class, not to the function.

## Reference

| Source | Content |
| --- | --- |
| [nvim-treesitter `main`](https://github.com/nvim-treesitter/nvim-treesitter/tree/main) | Setup of the rewritten plugin, without modules |
| [nvim-treesitter-textobjects `main`](https://github.com/nvim-treesitter/nvim-treesitter-textobjects/tree/main) | Functions to call from key mappings |
