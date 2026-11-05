from dataclasses import fields

import pytest

from pcr12 import __main__ as cli
from pcr12.errors import ModelError
from tests.conftest import Machine


def _options(machine: Machine) -> list[str]:
    options = []
    for field in fields(machine.paths):
        options += ["--" + field.name.replace("_", "-"), str(getattr(machine.paths, field.name))]
    return options


def test_check_command_writes_the_marker(machine: Machine) -> None:
    machine.boot()
    assert cli.run([*_options(machine), "check"]) == 0
    assert machine.paths.marker.exists()


def test_check_command_raises_on_a_changed_esp(machine: Machine) -> None:
    machine.boot()
    machine.write_policy(b"changed")
    with pytest.raises(ModelError):
        cli.run([*_options(machine), "check"])
