{ config, pkgs, ... }:
{
  custom.network.opensnitch = {
    allowedExecutables = {
      git-remote-http = "${pkgs.git}/libexec/git-core/git-remote-http";
      ssh = "${config.programs.ssh.package}/bin/ssh";
      curl = "${pkgs.curl.bin}/bin/curl";
      wget = "${pkgs.wget}/bin/wget";
      python3 = "${pkgs.python3}/bin/${pkgs.python3.executable}";
      go = "${pkgs.go}/share/go/bin/go";
      terraform = "${pkgs.terraform}/bin/terraform";
      helm = "${pkgs.kubernetes-helm}/bin/helm";
      kubectl = "${pkgs.kubectl}/bin/kubectl";
      flux = "${pkgs.fluxcd}/bin/flux";
      clusterctl = "${pkgs.clusterctl}/bin/clusterctl";
      kind = "${pkgs.kind}/bin/kind";
      trivy = "${pkgs.trivy}/bin/trivy";
      spotify = "${pkgs.spotify}/share/spotify/.spotify-wrapped";
      libreoffice = "${pkgs.libreoffice-qt.unwrapped}/lib/libreoffice/program/soffice.bin";
    };
    allowedExecutablePatterns = {
      discord = "^/nix/store/[a-z0-9]{32}-discord-unwrapped-[^/]+/opt/Discord/\\.Discord-wrapped$";
      terraform-providers = "^/home/[^/]+/.+/\\.terraform/providers/registry\\.terraform\\.io/hashicorp/[^/]+/[^/]+/linux_amd64/terraform-provider-[^/]+$";
    };
  };
}
