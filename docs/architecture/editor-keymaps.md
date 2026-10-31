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

### Selecting, cutting and pasting

Deleting cuts: `d`, `c` and `x` put the text in the clipboard, like `y` copies it, and `p` pastes
it. The clipboard is the one of the desktop, so text copied in Firefox pastes with `p`. A selection
made with the mouse is a visual mode selection, so every key of the visual mode applies to it.

| Keys | Action | Origin |
| --- | --- | --- |
| `v` / `V` / `Ctrl+V` | Start selecting characters / whole lines / a rectangle | Native |
| A motion in visual mode | Extend the selection: `w` next word, `e` end of word, `b` previous word, `j` / `k` line below / above, `$` end of line, `_` start of line, `G` end of file, `gg` start of file | Native |
| A text object in visual mode | Select it: `iw` word, `i"` inside quotes, `i(` inside parentheses, `ip` paragraph, `af` function | Native |
| `o` in visual mode | Move the cursor to the other end of the selection | Native |
| `d` / `y` / `c` on a selection | Cut / copy / delete and type the replacement | Native |
| `p` / `P` | Paste after / before the cursor; lines go below / above; on a selection, replace it | Native |
| `dd` / `yy` / `cc` | Cut / copy / rewrite the whole line; `3dd` cuts three lines | Native |
| `d`, `y` or `c` followed by a motion or a text object | Act without selecting: `dw` a word, `d$` to the end of the line, `diw` the word under the cursor, `ci"` inside quotes, `dap` a paragraph | Native |
| `x` | Cut the character under the cursor | Native |
| `"_d` | Delete without touching the clipboard | Native |
| `u` / `Ctrl+R` | Undo / redo | Native |
| `.` | Repeat the last change | Native |

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

### Diagnostics

Errors and warnings of the language server and of the linter are underlined, marked in the margin
and their message shows at the end of the line, errors first. The linter runs when a file is opened
or saved. Trouble lists them in a panel, like the problems panel of an IDE.

| Keys | Action | Origin |
| --- | --- | --- |
| `]d` / `[d` | Go to the next / previous diagnostic; needs AltGr on an AZERTY keyboard | Native |
| `Ctrl+W d` | Show the full message of the diagnostic under the cursor in a popup | Native |
| `<leader>xx` | List the diagnostics of the project in Trouble | Config |
| `<leader>xb` | List the diagnostics of the current file in Trouble | Config |
| `<leader>cs` | List the symbols of the file in Trouble, like an outline panel | Config |
| `<leader>cl` | List the definitions, references and implementations of the symbol in Trouble | Config |
| `<leader>xq` / `<leader>xl` | Show the quickfix list / location list in Trouble | Config |

In the Trouble panel:

| Keys | Action | Origin |
| --- | --- | --- |
| `Enter` | Go to the location | Plugin |
| `p` | Preview the location | Plugin |
| `q` | Close the panel | Plugin |
| `?` | List every key of the panel | Plugin |

The quickfix list is one list for the whole editor, filled for example by `Ctrl+Q` in a search. The
location list belongs to a window, filled for example by `gO`.

| Keys | Action | Origin |
| --- | --- | --- |
| `:copen` / `:cclose` | Open / close the quickfix list | Native |
| `:cn` / `:cp` | Go to the next / previous entry of the quickfix list | Native |
| `]q` / `[q` | Same as `:cn` / `:cp`; needs AltGr on an AZERTY keyboard | Native |
| `:lopen`, `:ln`, `:lp` | Same for the location list; `]l` / `[l` with AltGr | Native |
| `Enter` in a list | Go to the location of the entry | Native |

### Completion

In insert mode, a menu of suggestions opens while typing: `[LSP]` from the language server,
`[Snip]` snippets, `[Path]` file paths, `[Buf]` words of the open files from three letters. No
suggestion is selected when the menu opens. Without the menu, these keys keep their usual meaning.

| Keys | Action | Origin |
| --- | --- | --- |
| `Ctrl+Space` | Open the menu | Config |
| `Tab` / `Shift+Tab` | Select the next / previous suggestion; in a snippet, go to the next / previous field | Config |
| `Down` / `Up`, `Ctrl+J` / `Ctrl+K` | Select the next / previous suggestion | Config |
| `Space` | Insert the selected suggestion and a space; a plain space when nothing is selected | Config |
| `Enter` | Always a new line, never a suggestion | Native |
| `Ctrl+E` | Close the menu without inserting | Config |
| `Ctrl+B` / `Ctrl+F` | Scroll the documentation of the suggestion | Config |
| `Ctrl+N` / `Ctrl+P` | Native completion from the words of the open files | Native |
| `Ctrl+X` then `Ctrl+F` | Native completion of a file path | Native |
| `Ctrl+X` then `Ctrl+L` | Native completion of a whole line already written | Native |

### Code structure (Treesitter)

Treesitter parses the code into functions, classes and parameters. Its text objects combine with
the native operators: `d` deletes, `c` changes, `y` copies and `v` selects, so `daf` deletes a
whole function and `cif` replaces its body.

| Keys | Action | Origin |
| --- | --- | --- |
| `v` then `an` | Select the enclosing node, wider at each press | Native |
| `in` in visual mode | Select the inner node, narrower at each press | Native |
| `]n` / `[n` in visual mode | Select the next / previous node; needs AltGr on an AZERTY keyboard | Native |
| `af` / `if` | A whole function / the body of the function, after an operator or in visual mode | Config |
| `ac` / `ic` | A whole class / the body of the class | Config |
| `aa` / `ia` | A parameter with its separator / the parameter alone | Config |
| `]m` / `[m` | Go to the start of the next / previous function; needs AltGr on an AZERTY keyboard | Config |
| `]]` / `[[` | Go to the start of the next / previous class; needs AltGr on an AZERTY keyboard | Config |

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

### Terminal

The integrated terminal has two modes: in terminal mode the keys go to the shell; in normal mode its
output is plain text to scroll, search with `/` and copy with `y`.

| Keys | Action | Origin |
| --- | --- | --- |
| `F12` | Open or close the floating terminal, from any mode | Config |
| `2` then `F12` | Open or close a second terminal, distinct from the first | Plugin |
| `<leader>tf` | Open or close the floating terminal | Config |
| `<leader>th` | Open or close the terminal at the bottom of the screen | Config |
| `Esc` `Esc` | Leave terminal mode for normal mode; a single `Esc` goes to the program | Config |
| `Ctrl+\` then `Ctrl+N` | Leave terminal mode for normal mode | Native |
| `i` | Go back to terminal mode to type in the shell | Native |
| `:terminal` | Open a terminal in the current window | Native |

### Sessions

The files left open when Neovim exits are saved for the current directory, and reopened only on
request.

| Keys | Action | Origin |
| --- | --- | --- |
| `<leader>ss` | Save the session of this directory now | Config |
| `<leader>sr` | Reopen the files left open at the last exit from this directory | Config |
| `<leader>sd` | Delete the session of this directory | Config |
| `<leader>sl` | Search every saved session and open one | Config |

### Editing helpers

Brackets and quotes are closed as they are typed, except in strings and comments; typing the
closing character over an existing one steps over it, and `Backspace` between an empty pair
deletes both.

| Keys | Action | Origin |
| --- | --- | --- |
| `gcc` | Comment or uncomment the line | Native |
| `gc` with a motion or in visual mode | Comment or uncomment the lines, such as `gcap` for a paragraph | Native |
| `ys` with a text object and a character | Surround: `ysiw"` turns `word` into `"word"` | Plugin |
| `ds` with a character | Delete the surrounding pair: `ds"` | Plugin |
| `cs` with the old and new characters | Change the surrounding pair: `cs"'` | Plugin |
| `S` with a character in visual mode | Surround the selection | Plugin |
| `b`, `B`, `r` as surround characters | Stand for `)`, `}` and `]`, which avoids AltGr: `ysiwB` gives `{word}` | Plugin |
| `(` / `)` as surround characters | With / without spaces inside: `( word )` / `(word)` | Plugin |

### Markdown

Markdown files are rendered in place: headings, tables, checkboxes and callouts such as
`> [!note]` are drawn, and the line under the cursor shows its raw text. Obsidian, opened on the
same directory, shows the full rendering, Mermaid graphs included.

| Keys | Action | Origin |
| --- | --- | --- |
| `:RenderMarkdown toggle` | Switch between the rendered and the raw view of the file | Plugin |

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
