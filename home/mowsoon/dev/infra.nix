{ lib, pkgs, ... }:
{
  home.packages = with pkgs; [
    kubectl
    kubectx
    kubernetes-helm
    fluxcd
    clusterctl
    kind
    terraform
    ansible
    trivy
    postgresql
  ];

  programs = {
    kubecolor.enable = true;

    zsh.initContent = ''
      autoload -U +X bashcompinit && bashcompinit
      complete -o nospace -C ${lib.getExe pkgs.terraform} terraform
    '';
  };
}
