{ inputs, ... }:
let
  identity = import "${inputs.nixos-private}/home/mowsoon/kernel-identity.nix";
in
{
  systemd.user.tmpfiles.rules = [ "v %h/src/kernel/build - - - -" ];

  programs.git.includes = [
    {
      condition = "gitdir:~/src/kernel/";
      contents = {
        user = { inherit (identity) name email; };
        b4.send-endpoint-web = "https://lkml.kernel.org/_b4_submit";
        sendemail = {
          confirm = "always";
          suppresscc = "self";
        };
      };
    }
  ];
}
