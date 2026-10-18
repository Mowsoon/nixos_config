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

        "3rdparty".Extensions."uBlock0@raymondhill.net".toOverwrite.filterLists = [
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

    custom.network.opensnitch.allowedExecutables.firefox =
      "${config.programs.firefox.finalPackage}/lib/firefox/firefox";
  };
}
