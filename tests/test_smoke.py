"""Smoke tests: the environment is set up and each dependency works offline."""

import importlib
import sys

import pytest


def test_python_version():
    assert sys.version_info >= (3, 14)


@pytest.mark.parametrize(
    "module", ["anser", "astropy", "astroquery", "duckdb", "pyarrow"]
)
def test_imports(module):
    importlib.import_module(module)


def test_duckdb_reads_arrow():
    import duckdb
    import pyarrow as pa

    stars = pa.table({"hip": [91262, 97649, 102098], "name": ["Vega", "Altair", "Deneb"]})
    rows = duckdb.sql("SELECT count(*) FROM stars").fetchall()
    assert rows == [(3,)]


def test_astropy_finds_constellations():
    from astropy.coordinates import SkyCoord

    # Summer Triangle, J2000 positions in degrees.
    vega = SkyCoord(279.2347, 38.7837, unit="deg")
    altair = SkyCoord(297.6958, 8.8683, unit="deg")
    deneb = SkyCoord(310.3580, 45.2803, unit="deg")

    assert vega.get_constellation() == "Lyra"
    assert altair.get_constellation() == "Aquila"
    assert deneb.get_constellation() == "Cygnus"
