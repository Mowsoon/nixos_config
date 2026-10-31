let
  rebuild = action: "nixos-rebuild ${action} --flake ~/.config/nixos#hephaestus --elevate sudo";
in
{
  programs.zsh.shellAliases = {
    sudo = "sudo ";
    rm = "rm -I --preserve-root";
    cp = "cp -i";
    mv = "mv -i";
    ll = "eza -l";
    la = "eza -la";
    lt = "eza --tree --level=2";
    grep = "grep --color=auto";
    diff = "diff --color=auto";
    ip = "ip -color=auto";
    cpv = "rsync -ah --info=progress2";
    kubectl = "kubecolor";
    k = "kubectl";
    f = "flux";
    cctl = "clusterctl";
    tf = "terraform";

    nrs = rebuild "switch";
    nrt = rebuild "test";
    nrb = rebuild "boot";
    nrbr = "${rebuild "boot"} && systemctl reboot";
    nrr = "sudo nixos-rebuild switch --rollback";
    nkern = "readlink /run/booted-system/kernel /run/current-system/kernel";
    cdn = "cd ~/.config/nixos";
    n = "nvim";

    hib = "systemctl hibernate";
    sus = "systemctl suspend";
    sush = "systemctl suspend-then-hibernate";

    jb = "journalctl -b";
    jbu = "journalctl -b --no-pager -u";
    jke = "journalctl -k -p err";

    gst = "git status";
    gaa = "git add -A";
    gcm = "git commit -m";
  };
}
