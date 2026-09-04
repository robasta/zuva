"""The package exports are lazy to avoid a circular import during setup.py."""
import pytest

import sunsynk


@pytest.mark.parametrize("name", sunsynk.__all__)
def test_every_exported_name_resolves(name):
    assert getattr(sunsynk, name).__name__ == name


def test_unknown_names_still_raise_attribute_error():
    with pytest.raises(AttributeError, match="no attribute 'Nope'"):
        sunsynk.Nope  # pylint: disable=pointless-statement
