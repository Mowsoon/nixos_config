{ pkgs, ... }:
{
  home = {
    packages = with pkgs; [
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

  programs = {
    direnv = {
      enable = true;
      nix-direnv.enable = true;
      config.global.hide_env_diff = true;
    };

    bat = {
      enable = true;
      config.theme = "base16";
    };

    eza = {
      enable = true;
      enableZshIntegration = false;
      icons = "auto";
      git = true;
    };

    kubecolor.enable = true;
  };
}
