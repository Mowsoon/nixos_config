{
  programs.nixvim.userCommands = {
    # Force Save
    W = {
      command = "w !sudo tee % > /dev/null";
      desc = "Save file with sudo";
    };
    # Trim Spaces
    TrimWhitespace = {
      command = "%s/\\s\\+$//e";
      desc = "Remove trailing whitespace";
    };
  };
}
