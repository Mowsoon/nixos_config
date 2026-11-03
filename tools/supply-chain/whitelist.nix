let
  until = "2027-05-03";
  group =
    package: reason: vulns:
    map (vuln: {
      inherit
        vuln
        package
        reason
        until
        ;
    }) vulns;
in
group "mujs"
  "NVD bounds the affected versions by a 2016 or 2017 date or commit, or not at all, which grype compares with 1.3.6 as a number; fixed upstream in 2016 and 2017"
  [
    "CVE-2016-7504"
    "CVE-2016-7506"
    "CVE-2016-7563"
    "CVE-2016-7564"
    "CVE-2016-9017"
    "CVE-2016-9108"
    "CVE-2016-9109"
    "CVE-2016-9136"
    "CVE-2016-9294"
    "CVE-2016-10132"
    "CVE-2016-10133"
    "CVE-2016-10141"
    "CVE-2017-5627"
    "CVE-2017-5628"
  ]
++ group "spice" "NVD CPE without a version bound; fixed upstream in 2016 and 2018, before 0.16.0" [
  "CVE-2016-0749"
  "CVE-2016-2150"
  "CVE-2018-10893"
]
++
  group "imagemagick"
    "NVD CPE without a version bound; fixed upstream in ImageMagick 6.9 and 7.0, before 7.1.2"
    [
      "CVE-2014-9826"
      "CVE-2016-7538"
      "CVE-2017-5506"
    ]
++
  group "imagemagick"
    "NVD bound is < 7.1.2; grype reads 7.1.2-31 as a prerelease of 7.1.2, while ImageMagick numbers patch releases after it"
    [
      "CVE-2023-5341"
    ]
++
  group "kde-cli-tools" "kdesu, fixed in kde-cli-tools 5.7.5 in 2016; NVD CPE without a version bound"
    [
      "CVE-2016-7787"
    ]
++
  group "typescript"
    "Visual Studio and Azure Storage Explorer, fixed in 2020; NVD CPE without a version bound"
    [
      "CVE-2020-1416"
    ]
++ group "samba" "Samba on HP NonStop Server only" [ "CVE-2011-2411" ]
++ group "strace" "Race on Linux 2.3.20 only" [ "CVE-2000-0006" ]
++ group "cups" "AppArmor profile of the Ubuntu cups package" [ "CVE-2018-6553" ]
++ group "postgresql" "Cluster scripts of the Debian postgresql-common package" [ "CVE-2017-8806" ]
++
  group "bluez"
    "Bluetooth stack of the Linux kernel, fixed in Linux 5.8; the BlueZ user space is not affected"
    [
      "CVE-2020-24490"
    ]
++ group "openvpn" "NVD CPE limited to Windows (target_sw windows)" [
  "CVE-2026-81738"
  "CVE-2026-84256"
]
++
  group "gnupg"
    "Fixed by the FreePG patch 0019, Disallow compressed signatures and certificates (GnuPG T5993), applied by nixpkgs"
    [
      "CVE-2022-3219"
    ]
++ group "libxslt" "Fixed by libxslt merge request 77 (issue 144), applied by nixpkgs" [
  "CVE-2025-10911"
]
++ group "snappy" "NVD CPE is knplabs/snappy, a PHP library, not the Google compression library" [
  "CVE-2023-28115"
  "CVE-2023-41330"
]
++ group "shellcheck" "NVD CPE is the Visual Studio Code extension (target_sw visual_studio_code)" [
  "CVE-2021-28794"
]
++ group "thrift" "NVD CPE is Facebook fbthrift, not Apache Thrift" [ "CVE-2021-24028" ]
++ group "orc" "NVD CPE is Apache ORC, not the GStreamer orc compiler" [ "CVE-2025-47436" ]
++
  group "lapack" "nixpkgs lapack 3 is the LAPACK ABI of OpenBLAS 0.3.33; fixed in OpenBLAS 0.3.18"
    [
      "CVE-2021-4048"
    ]
