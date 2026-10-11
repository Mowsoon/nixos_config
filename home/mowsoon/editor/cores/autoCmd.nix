{
  programs.nixvim.autoCmd = [
    # Python
    {
      event = [ "FileType" ];
      pattern = [ "python" ];
      command = "setlocal shiftwidth=4 tabstop=4 softtabstop=4 expandtab";
    }
    # Go
    {
      event = [ "FileType" ];
      pattern = [ "go" ];
      command = "setlocal shiftwidth=4 tabstop=4 softtabstop=4 noexpandtab";
    }
    # Makefiles
    {
      event = [ "FileType" ];
      pattern = [ "make" ];
      command = "setlocal shiftwidth=4 tabstop=4 softtabstop=4 noexpandtab";
    }
  ];
}
