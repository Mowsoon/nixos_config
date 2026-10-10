{
  imports = [
    ../../modules/network/manager.nix
    ../../modules/network/dns.nix
    ../../modules/network/firewall.nix
    ../../modules/network/tuning.nix
    ../../modules/network/opensnitch.nix
  ];

  custom.network = {
    manager.enable = true;
    dns.enable = true;
    firewall.enable = true;
    tuning.enable = true;
    opensnitch.enable = true;
  };
}
