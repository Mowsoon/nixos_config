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
