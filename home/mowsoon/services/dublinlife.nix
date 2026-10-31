{ config, ... }:
{
  services.dublinlife = {
    enable = true;
    contentDir = "${config.home.homeDirectory}/Projects/DublinLife/content";
  };
}
