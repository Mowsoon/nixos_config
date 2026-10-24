{ python3Packages }:
python3Packages.buildPythonApplication {
  pname = "rgb-effects";
  version = "0.1.0";
  pyproject = true;
  src = ./.;

  build-system = [ python3Packages.poetry-core ];

  dependencies = [
    python3Packages.openrgb-python
    python3Packages.dbus-fast
    python3Packages.evdev
  ];

  nativeCheckInputs = [
    python3Packages.pytestCheckHook
    python3Packages.pytest-asyncio
    python3Packages.black
    python3Packages.flake8
    python3Packages.flake8-bugbear
    python3Packages.bandit
  ];

  preCheck = ''
    black --check src tests
    flake8 src tests
    bandit -q -c pyproject.toml -r src
  '';

  meta.mainProgram = "rgb-effects";
}
