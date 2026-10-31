# Editor key mappings

## Overview

This sheet lists the Neovim key mappings group by group, as G2 shows them. Text editing is learned
through the native Vim commands; mappings are added only for actions an IDE puts behind a shortcut,
such as the file explorer. The Origin column tells which keys work in any Vim (`Native`), which
come from a plugin default (`Plugin`) and which this configuration declares (`Config`). The sheet
holds only the groups already reviewed.

`<leader>` is the space bar. `Ctrl+W h` means Ctrl+W, released, then `h`. Mappings of the explorer
apply only while the cursor is in the explorer window.

## Reference

### Windows

| Keys | Action | Origin |
| --- | --- | --- |
| `Ctrl+W h` / `Ctrl+W l` | Go to the window on the left / on the right, such as the explorer | Native |
| `Ctrl+W w` | Go to the next window, in a loop | Native |
| `Ctrl+W p` | Go back to the previous window | Native |
| `:q` | Close the current window, not the file | Native |
| `:qa` | Quit Neovim | Native |

### Open files

An open file is a buffer, shown as a numbered tab in the buffer line at the top. Closing a window
with `:q` leaves its file open in the background. The tabs are sorted by directory, then by name,
and the numbers follow that order.

| Keys | Action | Origin |
| --- | --- | --- |
| `Tab` / `Shift+Tab` | Go to the next / previous file of the buffer line | Config |
| `Alt` with a key of the number row, `&` to `ç` | Go to the file with that number in the buffer line, counting the visible tabs | Config |
| Left click on a tab of the buffer line | Go to that file | Plugin |
| `<leader>fb` | Pick an open file by fuzzy search on its name | Config |
| `:BufferLinePick` | Show a letter on each tab, then go to the tab whose letter is typed | Plugin |
| `<leader>bd` | Close the current file and keep its window | Config |
| Right click on a tab of the buffer line | Close that file and keep its window | Config |
| `:e <path>` | Open a file; `Tab` completes the path | Native |
| `:w` / `:wa` | Save the current file / every file | Native |
| `:ls` | List the open files with their number | Native |
| `:b <number>` / `:b <name>` | Go to the file with that number, or whose name contains that text | Native |
| `:bn` / `:bp` | Go to the next / previous file | Native |
| `]b` / `[b` | Go to the next / previous file; needs AltGr on an AZERTY keyboard | Native |
| `Ctrl+^` / `:b#` | Go back to the previous file, back and forth | Native |
| `<leader>a` | Show the dashboard | Config |
| `<leader>sr` | Reopen the files left open at the last exit from this directory | Config |

### Search

The search window filters as you type and previews the selected result. Searches by name and by
content include hidden files, but not `.git/` nor what `.gitignore` excludes.

| Keys | Action | Origin |
| --- | --- | --- |
| `<leader>ff` | Search a file by name | Config |
| `<leader>fg` | Search a text in every file of the project | Config |
| `<leader>fr` | Search the recently opened files | Config |
| `<leader>fh` | Search the Neovim help | Config |
| `:Telescope keymaps` | Search every active key mapping | Plugin |
| `/text` then `Enter` | Search forward in the current file; `/` is `Shift+:` on AZERTY | Native |
| `?text` then `Enter` | Search backward in the current file; `?` is `Shift+,` on AZERTY | Native |
| `n` / `N` | Go to the next / previous match | Native |
| `*` | Search the word under the cursor | Native |
| `Esc` | Clear the highlight of the last search | Config |

In the search window:

| Keys | Action | Origin |
| --- | --- | --- |
| `Ctrl+J` / `Ctrl+K` | Go to the next / previous result | Config |
| `Down` / `Up`, `Ctrl+N` / `Ctrl+P` | Go to the next / previous result | Plugin |
| `Enter` | Open the result | Plugin |
| `Ctrl+X` / `Ctrl+V` | Open the result in a split below / beside | Plugin |
| `Ctrl+U` / `Ctrl+D` | Scroll the preview up / down | Plugin |
| `Tab` | Select several results | Plugin |
| `Ctrl+Q` | Send every result to the quickfix list and open it | Plugin |
| `Ctrl+/` | List every key of the search window | Plugin |
| `Esc` | Close the search window | Config |

### Code (LSP)

The language server of the file type understands the code. Its keys work only in a file it is
attached to.

| Keys | Action | Origin |
| --- | --- | --- |
| `gd` / `gD` | Go to the definition / declaration | Config |
| `Ctrl+]` | Go to the definition; needs AltGr on an AZERTY keyboard | Native |
| `grr` | List the references | Native |
| `gri` | List the implementations | Native |
| `grt` | Go to the definition of the type | Native |
| `grn` | Rename the symbol everywhere | Native |
| `gra` | Code actions on the cursor or the selection, such as quick fixes | Native |
| `gO` | List the symbols of the file | Native |
| `K` | Show the documentation of the symbol under the cursor | Native |
| `Ctrl+S` in insert mode | Show the signature of the function being called | Native |
| `Ctrl+O` / `Ctrl+I` | Go back / forward to the previous / next position, such as after `gd` | Native |
| `<leader>cf` | Format the file; saving formats it too | Config |

### Git

Fugitive runs the Git commands of the repository; gitsigns marks the changed lines in the margin
and works on hunks, the blocks of consecutive changed lines. The author and date of the last commit
of the line under the cursor show in grey at its end.

| Keys | Action | Origin |
| --- | --- | --- |
| `<leader>gs` | Open the Git status window | Config |
| `<leader>gd` | Show the changes of the current file side by side | Config |
| `<leader>gc` | Commit | Config |
| `<leader>gp` | Push | Config |
| `<leader>gl` | Show the history, one line per commit | Config |
| `<leader>gb` | Show the full blame of the line in a popup | Config |
| `]c` / `[c` | Go to the next / previous hunk; in a side-by-side diff, the next / previous difference | Config / Native |
| `<leader>hp` | Preview the hunk: its previous content in a popup | Config |
| `<leader>hs` | Stage the hunk, or the selected lines in visual mode | Config |
| `<leader>hr` | Reset the hunk, or the selected lines in visual mode, to the last commit | Config |

In the Git status window:

| Keys | Action | Origin |
| --- | --- | --- |
| `s` / `u` / `-` | Stage / unstage / toggle the file under the cursor | Plugin |
| `=` | Expand the diff of the file under the cursor in place | Plugin |
| `dv` | Show the diff of the file side by side | Plugin |
| `X` | Discard the changes of the file, for good | Plugin |
| `cc` | Commit | Plugin |
| `Enter` | Open the file | Plugin |
| `g?` / `gq` | Help / close the window | Plugin |

A commit opens its message in a buffer: `i` to type, `Esc`, then `:wq` to save and commit, or `:q!`
to quit without saving; an empty message aborts the commit.

### Macros

| Keys | Action | Origin |
| --- | --- | --- |
| `qa` | Start recording the keys typed into register `a` | Native |
| `q` | Stop recording | Native |
| `@a` | Replay the keys recorded in register `a` | Native |

### File explorer

| Keys | Action | Origin |
| --- | --- | --- |
| `<leader>e` | Open or close the explorer | Config |
| `q` | Close the explorer | Plugin |
| `?` | List every key of the explorer | Plugin |
| `Enter` | Open a file, expand or collapse a directory | Plugin |
| `s` / `v` | Open the file in a split below / beside | Config |
| `a` | Create a file; a name ending with `/` creates a directory | Plugin |
| `A` | Create a directory | Plugin |
| `r` | Rename | Plugin |
| `m` | Move to a path typed at the prompt | Plugin |
| `c` / `x` / `p` | Copy / cut / paste | Config / Plugin / Plugin |
| `d` | Move to the trash, without confirmation | Config |
| `u` | Undo the last trash, which restores the file | Plugin |
| `y` | Copy the path of the file to the clipboard | Config |
| `h` | Show or hide hidden files | Config |
| `R` | Refresh | Plugin |
| `P` | Preview the file in a floating window | Plugin |
| `/` | Fuzzy search in the tree | Plugin |
| `.` / `Backspace` | Make the directory the root / go up one level | Plugin |
| `<` / `>` | Switch between the Files, Buffers and Git views | Plugin |
| `[g` / `]g` | Previous / next file modified in Git | Plugin |
| `z` | Collapse every directory | Plugin |
| `Tab` | Select several files for the next action | Plugin |
| `i` | Show the size and dates of the file | Plugin |
| `o` then a letter | Sort: `on` name, `om` modification date, `os` size, `ot` type | Plugin |
