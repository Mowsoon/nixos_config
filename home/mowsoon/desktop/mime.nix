let
  browser = "firefox.desktop";
  editor = "nvim.desktop";
  pdfViewer = "org.pwmt.zathura-pdf-mupdf.desktop";
  imageViewer = "org.kde.gwenview.desktop";
  mediaPlayer = "mpv.desktop";
  fileManager = "org.kde.dolphin.desktop";
  archiver = "org.kde.ark.desktop";
in
{
  programs = {
    zathura.enable = true;
    mpv.enable = true;
  };

  xdg = {
    mimeApps = {
      enable = true;
      defaultApplications = {
        "text/html" = browser;
        "application/xhtml+xml" = browser;
        "x-scheme-handler/http" = browser;
        "x-scheme-handler/https" = browser;
        "x-scheme-handler/about" = browser;
        "x-scheme-handler/unknown" = browser;

        "text/*" = editor;
        "application/json" = editor;
        "application/xml" = editor;
        "application/x-yaml" = editor;
        "application/toml" = editor;
        "application/x-shellscript" = editor;

        "application/pdf" = pdfViewer;
        "image/*" = imageViewer;
        "video/*" = mediaPlayer;
        "audio/*" = mediaPlayer;
        "inode/directory" = fileManager;

        "application/zip" = archiver;
        "application/x-tar" = archiver;
        "application/x-compressed-tar" = archiver;
        "application/x-zstd-compressed-tar" = archiver;
        "application/gzip" = archiver;
        "application/x-7z-compressed" = archiver;
        "application/vnd.rar" = archiver;
      };
    };

    configFile."mimeapps.list".force = true;
    dataFile."applications/mimeapps.list".force = true;
  };
}
