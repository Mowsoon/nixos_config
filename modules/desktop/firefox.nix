{ config, lib, ... }:
let
  cfg = config.custom.firefox;
  fromAmo = slug: "https://addons.mozilla.org/firefox/downloads/latest/${slug}/latest.xpi";
  forcedExtension = slug: {
    installation_mode = "force_installed";
    install_url = fromAmo slug;
    private_browsing = true;
    default_area = "navbar";
  };
  allowedThirdParties = {
    "site-1.example" = [
      "host-1.example"
      "host-2.example"
    ];
    "site-2.example" = [
      "host-3.example"
      "site-3.example"
    ];
    "site-4.example" = [ "host-4.example" ];
  };
  ublockDefaultRules = [
    "behind-the-scene * * noop"
    "behind-the-scene * image noop"
    "behind-the-scene * 3p noop"
    "behind-the-scene * inline-script noop"
    "behind-the-scene * 1p-script noop"
    "behind-the-scene * 3p-script noop"
    "behind-the-scene * 3p-frame noop"
  ];
  ublockMediumMode = [
    "* * 3p-script block"
    "* * 3p-frame block"
  ];
  ublockAllowances = lib.concatLists (
    lib.mapAttrsToList (site: hosts: map (host: "${site} ${host} * noop") hosts) allowedThirdParties
  );
  ublockDynamicRules = lib.concatStringsSep "\n" (
    ublockDefaultRules ++ ublockMediumMode ++ ublockAllowances
  );
in
{
  options.custom.firefox = {
    enable = lib.mkEnableOption "Firefox with declared extensions, search engine and privacy settings";
  };

  config = lib.mkIf cfg.enable {
    programs.firefox = {
      enable = true;

      preferences = {
        "dom.security.https_first" = true;
        "media.peerconnection.ice.default_address_only" = true;
        "network.IDN_show_punycode" = true;
        "privacy.globalprivacycontrol.enabled" = true;
      };

      policies = {
        DisableTelemetry = true;
        DisableFirefoxStudies = true;
        PasswordManagerEnabled = false;
        OfferToSaveLogins = false;
        AutofillAddressEnabled = false;
        AutofillCreditCardEnabled = false;

        DNSOverHTTPS = {
          Enabled = false;
          Locked = true;
        };

        EnableTrackingProtection = {
          Value = true;
          Category = "strict";
          Locked = true;
        };

        FirefoxHome = {
          SponsoredTopSites = false;
          SponsoredStories = false;
        };

        FirefoxSuggest.SponsoredSuggestions = false;

        SearchEngines.Default = "DuckDuckGo";

        ExtensionSettings = {
          "uBlock0@raymondhill.net" = forcedExtension "ublock-origin";
          "{446900e4-71c2-419f-a6a7-df9c091e268b}" = forcedExtension "bitwarden-password-manager";
        };

        "3rdparty".Extensions."uBlock0@raymondhill.net" = {
          adminSettings = builtins.toJSON { dynamicFilteringString = ublockDynamicRules; };
          userSettings = [
            [
              "advancedUserEnabled"
              "true"
            ]
          ];
          toOverwrite.filterLists = [
            "user-filters"
            "ublock-filters"
            "ublock-badware"
            "ublock-privacy"
            "ublock-unbreak"
            "ublock-quick-fixes"
            "easylist"
            "easyprivacy"
            "adguard-spyware-url"
            "block-lan"
            "urlhaus-1"
            "curben-phishing"
            "plowe-0"
          ];
        };
      };
    };

    custom.network.opensnitch.allowedExecutables.firefox =
      "${config.programs.firefox.finalPackage}/lib/firefox/firefox";
  };
}
