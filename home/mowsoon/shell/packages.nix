{ pkgs, ... }:
{
  home.packages = with pkgs; [
    btop
    htop
    nvtopPackages.nvidia
    fd
    wl-clipboard
    ouch
    jq
    yq-go
    tree
    cloc
    strace
    tcpdump
    dnsutils
    wget
    unzip
    unrar
    visidata
    smartmontools
    lynis
  ];
}
