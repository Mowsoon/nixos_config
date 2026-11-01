lib:
lib.genAttrs
  [
    "/home"
    "/persist"
    "/var/log"
  ]
  (_: {
    neededForBoot = true;
  })
