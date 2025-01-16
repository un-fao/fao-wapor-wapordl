import importlib.util
import os
import pathlib

import numpy as np
import pytest
import wapordl
import wapordl.bounding_boxes
import wapordl.main
import wapordl.unit_convertor
from wapordl import (
    wapor_map,
    wapor_ts,
)

optional_packages = ["dask", "rioxarray", "xarray"]
use_xarray = all(
    [not isinstance(importlib.util.find_spec(x), type(None)) for x in optional_packages]
)
if use_xarray:
    import xarray as xr

module_path = wapordl.__path__[0]
assert "conda" not in module_path

test_data_folder = pathlib.Path(module_path).parent / "test_data"

@pytest.mark.skipif(condition=not use_xarray, reason="XArray not available")
def test_xarray_1(tmp_path):
    region = os.path.join(test_data_folder, "1237500.geojson")
    period = ["2021-01-12", "2021-01-25"]
    # print(tmp_path)
    wapordl.unit_convertor.use_xarray = False
    xx_1 = wapor_map(
        region,
        "L2-AETI-M",
        period,
        os.path.join(tmp_path, "no_xarray"),
        unit_conversion="day",
        overview=3,
    )
    wapordl.unit_convertor.use_xarray = True
    xx_2 = wapor_map(
        region,
        "L2-AETI-M",
        period,
        os.path.join(tmp_path, "ya_xarray"),
        unit_conversion="day",
        overview=3,
    )
    x1 = xr.open_dataset(xx_1)
    x2 = xr.open_dataset(xx_2)
    assert x1.mean() == x2.mean()

@pytest.mark.skipif(condition=not use_xarray, reason="XArray not available")
def test_xarray_2():

    region = os.path.join(test_data_folder, "1237500.geojson")
    period = ["2021-01-12", "2021-01-25"]
    wapordl.unit_convertor.use_xarray = False
    dff_1 = wapor_ts(region, "L2-AETI-M", period, unit_conversion="day", overview=3)
    wapordl.unit_convertor.use_xarray = True
    dff_2 = wapor_ts(region, "L2-AETI-M", period, unit_conversion="day", overview=3)
    assert dff_1.equals(dff_2)

@pytest.mark.skipif(condition=not use_xarray, reason="XArray not available")
def test_big_data(tmp_path):
    # BIG DATA, this crashes without Dask.
    wapordl.unit_convertor.use_xarray = True
    wapor_map(
        "ENO",
        "L3-T-D",
        ["2021-12-01", "2021-12-31"],
        os.path.join(tmp_path, "big_xarray"),
        unit_conversion="dekad",
    )

@pytest.mark.skipif(condition=not use_xarray, reason="XArray not available")
def test_summation(tmp_path):
    bb = [30.2, 28.6, 31.3, 30.5]
    period = ["2018-01-01", "2018-12-31"]

    fp_a_nc = wapordl.wapor_map(bb, "L2-AETI-A", period, tmp_path, extension=".nc")
    fp_d_nc = wapordl.wapor_map(bb, "L2-AETI-D", period, tmp_path, extension=".nc")
    fp_dd_nc = wapordl.wapor_map(
        bb, "L2-AETI-D", period, tmp_path, extension=".nc", unit_conversion="dekad"
    )

    ds_d = xr.open_dataset(fp_d_nc, decode_coords="all")
    coords = [
        np.datetime64(da.attrs["start_date"], "ns") for da in ds_d.data_vars.values()
    ]
    da_d = ds_d.to_array("time").assign_coords({"time": coords})
    length = xr.where(da_d["time"].dt.day != 21, 10, da_d["time"].dt.daysinmonth - 20)
    da_d = (da_d * length).sum(dim="time")

    ds_dd = xr.open_dataset(fp_dd_nc, decode_coords="all")
    coords = [
        np.datetime64(da.attrs["start_date"], "ns") for da in ds_dd.data_vars.values()
    ]
    da_dd = ds_dd.to_array("time").assign_coords({"time": coords})
    da_dd = da_dd.sum(dim="time")

    ds_a = xr.open_dataset(fp_a_nc, decode_coords="all")
    da_a = ds_a["Band1"]

    assert abs((da_a - da_d).mean().values) < 0.00001
    assert abs((da_a - da_dd).mean().values) < 0.00001
    assert abs((da_d - da_dd).mean().values) < 0.00001
