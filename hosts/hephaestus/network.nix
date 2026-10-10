{
  imports = [
    ../../modules/network/manager.nix
    ../../modules/network/dns.nix
    ../../modules/network/firewall.nix
    ../../modules/network/tuning.nix
  ];

  custom.network = {
    manager.enable = true;
    dns.enable = true;
    firewall.enable = true;
    tuning.enable = true;
  };
}
