{
  python3Packages,
  runCommand,
  ruff,
}:
let
  dependencies = [
    python3Packages.openrgb-python
    python3Packages.dbus-fast
    python3Packages.evdev
    python3Packages.numpy
  ];
  testDependencies = [
    python3Packages.pytest
    python3Packages.pytest-asyncio
  ];
  lint =
    name: tools: command:
    runCommand "rgb-effects-${name}" { nativeBuildInputs = tools; } ''
      cp -r ${./.} source
      chmod -R u+w source
      cd source
      ${command}
      touch $out
    '';
in
python3Packages.buildPythonApplication {
  pname = "rgb-effects";
  version = "0.1.0";
  pyproject = true;
  src = ./.;

  build-system = [ python3Packages.poetry-core ];

  inherit dependencies;

  nativeCheckInputs = [ python3Packages.pytestCheckHook ] ++ testDependencies;

  passthru.lints = {
    ruff = lint "ruff" [ ruff ] ''
      ruff format --no-cache --check src tests
      ruff check --no-cache src tests
    '';
    mypy = lint "mypy" [
      (python3Packages.python.withPackages (
        _: [ python3Packages.mypy ] ++ dependencies ++ testDependencies
      ))
    ] "mypy --cache-dir=/dev/null";
  };

  meta.mainProgram = "rgb-effects";
}
