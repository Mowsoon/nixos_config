{ pkgs, ... }:
{
  home = {
    packages = with pkgs; [
      btop
      htop
      nvtopPackages.nvidia
      fd
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
      trivy
      kubectl
      kubernetes-helm
      fluxcd
      clusterctl
      kind
      terraform
      azure-cli
      ansible
      postgresql
      go
      python3
    ];

    sessionPath = [ "$HOME/go/bin" ];
  };

  programs.direnv = {
    enable = true;
    nix-direnv.enable = true;
  };
}
