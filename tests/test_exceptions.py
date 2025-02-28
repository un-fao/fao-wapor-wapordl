import os
import pathlib

import pytest

import wapordl
import wapordl.products
import wapordl.products.wapor3
import wapordl.toolbox
import wapordl.toolbox.ogr_gdal
import wapordl.variable_descriptions

module_path = wapordl.__path__[0]
assert "conda" not in module_path

test_data_folder = pathlib.Path(module_path).parent / "test_data"


def test_extension_keyword():
    with pytest.raises(ValueError) as e:
        urls = []
        out_fn = "blabla.weirdext"
        _ = wapordl.toolbox.ogr_gdal.cog_dl(urls, out_fn)
    assert "Please use one of " in str(e.value)


def test_2():
    with pytest.raises(ValueError) as e:
        _ = wapordl.variable_descriptions.date_func(
            "https://storage.googleapis.com/fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-T-D/WAPOR-3.L3-T-D.BKA.2021-01-D1.tif",
            "W",
        )
    assert "Invalid temporal resolution." in str(e.value)


def test_3():
    with pytest.raises(ValueError) as e:
        _ = wapordl.variable_descriptions.collect_metadata("L4-AETI-D")
    assert "Invalid variable name" in str(e.value)


def test_4():
    with pytest.raises(ValueError) as e:
        _ = wapordl.products.wapor3.generate_urls(
            "L4-AETI-D", l3_region=None, period=None
        )
    assert "Invalid level " in str(e.value)


def test_5():
    period = ["2021-01-12", "2021-01-25"]
    overview = 3
    region = os.path.join(test_data_folder, "1237500.geojson")
    with pytest.raises(ValueError) as e:
        _ = wapordl.wapor_ts(
            region.replace(".geojson", "blabla.geojson"), "L1-AETI-A", period, overview
        )
    assert "Geojson file not found." in str(e.value)


def test_6():
    period = ["2021-01-12", "2021-01-25"]
    overview = 3
    with pytest.raises(ValueError) as e:
        _ = wapordl.wapor_ts([25, -17, 24, -16], "L1-AETI-A", period, overview)
    assert "Invalid bounding box." in str(e.value)


def test_7():
    period = ["2021-01-12", "2021-01-25"]
    overview = 3
    with pytest.raises(ValueError) as e:
        _ = wapordl.wapor_ts((500.0, "lala"), "L3-AETI-A", period, overview)
    assert "Invalid value for" in str(e.value)


def test_8():
    overview = 3
    region = os.path.join(test_data_folder, "1237500.geojson")
    with pytest.raises(ValueError) as e:
        _ = wapordl.wapor_ts(
            region, "L1-AETI-A", ["2021-01-15", "2021-01-01"], overview
        )
    assert "Invalid period." in str(e.value)


def test_11():
    overview = 3
    nodata_period = ["2015-01-01", "2016-01-01"]
    region = os.path.join(test_data_folder, "1237500.geojson")
    with pytest.raises(ValueError) as e:
        _ = wapordl.wapor_ts(region, "L2-AETI-D", nodata_period, overview)
    assert "No files found for selected region, variable and period." in str(e.value)


def test_12(tmp_path):
    period = ["2021-01-12", "2021-01-25"]
    region = os.path.join(test_data_folder, "1237500.geojson")
    with pytest.raises(ValueError) as e:
        _ = wapordl.wapor_map(
            region, "L2-AETI-D", period, tmp_path, unit_conversion="pentad"
        )
    assert "Please select one of " in str(e.value)


def test_13():
    period = ["2021-01-12", "2021-01-25"]
    overview = 3
    region = os.path.join(test_data_folder, "1237500.geojson")
    with pytest.raises(ValueError) as e:
        _ = wapordl.wapor_ts(
            region, "L2-AETI-D", period, overview, unit_conversion="pentad"
        )
    assert "Please select one of " in str(e.value)


def test_14(tmp_path):
    period = ["2021-01-12", "2021-01-25"]
    with pytest.raises(ValueError) as e:
        bb_south_america = [-68.203125, -18.979026, -55.371094, -9.839170]
        _ = wapordl.wapor_map(bb_south_america, "L2-T-D", period, tmp_path)
    assert "has no overlap with the datasets" in str(e.value)


def test_15(tmp_path):
    period = ["2021-01-12", "2021-01-25"]
    with pytest.raises(ValueError) as e:
        region_FAIL = os.path.join(test_data_folder, "test_FAIL.geojson")
        _ = wapordl.wapor_map(region_FAIL, "L3-T-D", period, tmp_path)
    assert "`region` can't be linked to any L3 region." in str(e.value)
