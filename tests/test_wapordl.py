import glob
import os

import pathlib

import numpy as np
import pandas as pd
import pytest
from osgeo import gdal, osr

import wapordl
import wapordl.bounding_boxes
import wapordl.main
import wapordl.overview_selector
import wapordl.unit_convertor
from wapordl import (
    wapor_map,
    wapor_ts,
)

module_path = wapordl.__path__[0]
assert "conda" not in module_path

test_data_folder = pathlib.Path(module_path).parent / "test_data"


#####
# PART 2
#####

fhs = [
    "detector_shapes/box_1.geojson",
    "detector_shapes/box_3.geojson",
    "detector_shapes/box_5.geojson",
    "detector_shapes/box_NONE.geojson",
]


@pytest.mark.parametrize("fh", fhs)
def test_overview_detector_1(fh, tmp_path):
    fh = os.path.join(test_data_folder, fh)
    x1 = wapordl.wapor_map(
        fh, "L1-T-D", ["2021-01-01", "2021-01-01"], tmp_path, overview="auto"
    )
    assert str(os.path.split(x1)[-1].split("_")[-2]) == os.path.split(fh)[-1].split(
        "_"
    )[-1].replace(".geojson", "")


def test_overview_detector_2(tmp_path):
    fh = os.path.join(test_data_folder, "detector_shapes/star.geojson")
    pngs = glob.glob(os.path.join(tmp_path, "*.png"))
    for png in pngs:
        os.remove(png)
    assert len(glob.glob(os.path.join(tmp_path, "*.png"))) == 0
    x5 = wapordl.wapor_map(
        fh,
        "L1-T-D",
        ["2021-01-01", "2021-01-01"],
        tmp_path,
        overview="AUTO",
        make_plots=tmp_path,
    )
    if wapordl.overview_selector.use_plt:
        assert len(glob.glob(os.path.join(tmp_path, "*.png"))) > 0
    pngs = glob.glob(os.path.join(tmp_path, "*.png"))
    for png in pngs:
        os.remove(png)

    fh = os.path.join(test_data_folder, "detector_shapes/tiny_box.geojson")
    x6 = wapordl.wapor_map(
        fh,
        "L1-T-D",
        ["2021-01-01", "2021-01-01"],
        os.path.join(tmp_path, "big_xarray"),
        overview="AUTO",
        max_error=0.001,
    )
    x6_overview = os.path.split(x6)[-1].split("_")[-2]
    if x6_overview == "NONE":
        x6_overview = -1
    assert int(os.path.split(x5)[-1].split("_")[-2]) > x6_overview


def test_overview_detector_3(tmp_path):
    fh = os.path.join(test_data_folder, "test_MUV.geojson")
    pngs = glob.glob(os.path.join(tmp_path, "*.png"))
    for png in pngs:
        os.remove(png)
    df1 = wapordl.wapor_ts(
        fh,
        "L3-AETI-D",
        ["2021-01-01", "2021-02-01"],
        overview="auto",
        make_plots=tmp_path,
        max_error=0.3,
    )
    assert df1["mean"].mean() > 2.5
    pngs = glob.glob(os.path.join(tmp_path, "*.png"))
    for png in pngs:
        os.remove(png)


#####
# AGERA5
#####


def test_agera5_1(tmp_path):
    region = os.path.join(test_data_folder, "1237500.geojson")
    period_agera5 = [
        (pd.Timestamp.now() - pd.Timedelta(days=80)).strftime("%Y-%m-%d"),
        (pd.Timestamp.now() - pd.Timedelta(days=40)).strftime("%Y-%m-%d"),
    ]
    _ = wapor_map(
        region,
        "AGERA5-ET0-D",
        period_agera5,
        tmp_path,
        extension=".nc",
        unit_conversion="dekad",
    )


def test_agera5_2(tmp_path):
    region = os.path.join(test_data_folder, "1237500.geojson")
    period_agera5 = [
        (pd.Timestamp.now() - pd.Timedelta(days=80)).strftime("%Y-%m-%d"),
        (pd.Timestamp.now() - pd.Timedelta(days=40)).strftime("%Y-%m-%d"),
    ]
    _ = wapor_map(
        region,
        "AGERA5-ET0-D",
        period_agera5,
        tmp_path,
        extension=".nc",
        unit_conversion="day",
    )


def test_agera5_3(tmp_path):
    region = os.path.join(test_data_folder, "1237500.geojson")
    period_agera5 = [
        (pd.Timestamp.now() - pd.Timedelta(days=80)).strftime("%Y-%m-%d"),
        (pd.Timestamp.now() - pd.Timedelta(days=40)).strftime("%Y-%m-%d"),
    ]
    _ = wapor_map(
        region,
        "AGERA5-ET0-E",
        period_agera5,
        tmp_path,
        extension=".nc",
        unit_conversion="dekad",
    )


def test_agera5_4(tmp_path):
    region = os.path.join(test_data_folder, "1237500.geojson")
    period_agera5 = [
        (pd.Timestamp.now() - pd.Timedelta(days=80)).strftime("%Y-%m-%d"),
        (pd.Timestamp.now() - pd.Timedelta(days=40)).strftime("%Y-%m-%d"),
    ]
    _ = wapor_map(region, "AGERA5-ET0-M", period_agera5, tmp_path)


def test_agera5_5():
    region = os.path.join(test_data_folder, "1237500.geojson")
    period_agera5 = [
        (pd.Timestamp.now() - pd.Timedelta(days=80)).strftime("%Y-%m-%d"),
        (pd.Timestamp.now() - pd.Timedelta(days=40)).strftime("%Y-%m-%d"),
    ]
    _ = wapor_ts(
        region, "AGERA5-TMAX-E", period_agera5, overview=3, unit_conversion="day"
    )


def test_agera5_6():
    region = os.path.join(test_data_folder, "1237500.geojson")
    period_agera5 = [
        (pd.Timestamp.now() - pd.Timedelta(days=80)).strftime("%Y-%m-%d"),
        (pd.Timestamp.now() - pd.Timedelta(days=40)).strftime("%Y-%m-%d"),
    ]
    _ = wapor_ts(
        region, "AGERA5-TMIN-E", period_agera5, overview="NONE", unit_conversion="month"
    )


def test_agera5_7():
    region = os.path.join(test_data_folder, "1237500.geojson")
    period_agera5 = [
        (pd.Timestamp.now() - pd.Timedelta(days=80)).strftime("%Y-%m-%d"),
        (pd.Timestamp.now() - pd.Timedelta(days=40)).strftime("%Y-%m-%d"),
    ]
    _ = wapor_ts(
        region, "AGERA5-RH12-E", period_agera5, overview=1, unit_conversion="year"
    )


def test_agera5_8(tmp_path):
    region = os.path.join(test_data_folder, "1237500.geojson")
    period_agera5 = ["2022-12-18", pd.Timestamp.now().strftime("%Y-%m-%d")]
    _ = wapor_map(region, "AGERA5-ET0-A", period_agera5, tmp_path)


#####
# GENERAL
#####


def test_general_1():
    overview = 3
    region = os.path.join(test_data_folder, "1237500.geojson")
    period = ["2021-01-12", "2021-01-25"]

    df1 = wapor_ts(region, "L2-AETI-D", period, overview=overview)
    assert np.isclose(df1.iloc[0]["mean"], 0.4291)
    assert df1.iloc[0].start_date == pd.Timestamp("2021-01-11 00:00:00")
    assert df1.attrs == {
        "long_name": "Actual EvapoTranspiration and Interception",
        "units": "mm/day",
        "overview": str(overview),
    }


def test_general_2():
    overview = 3
    region = os.path.join(test_data_folder, "1237500.geojson")
    period = ["2021-01-12", "2021-01-25"]
    df2 = wapor_ts(region, "L2-AETI-M", period, overview=overview)
    assert df2.attrs["units"] == "mm/month"


def test_general_3():
    overview = 3
    region = os.path.join(test_data_folder, "1237500.geojson")
    period = ["2021-01-12", "2021-01-25"]
    df3 = wapor_ts(region, "L2-AETI-A", period, overview=overview)
    assert df3.attrs["units"] == "mm/year"


variables = ["L1-AETI-D", "L1-AETI-M", "L1-AETI-A"]


@pytest.mark.parametrize("variable", variables)
def test_general_4(variable):
    overview = 3
    region = os.path.join(test_data_folder, "1237500.geojson")
    period = ["2021-01-12", "2021-01-25"]
    _ = wapor_ts(region, variable, period, overview=overview)


variables = [
    "L2-AETI-D",
    "L2-AETI-M",
    "L2-AETI-A",
    "L1-AETI-D",
    "L1-AETI-M",
    "L1-AETI-A",
]


@pytest.mark.parametrize("variable", variables)
def test_general_5(variable):
    overview = 3
    bb = [25, -17, 26, -16]
    period = ["2021-01-12", "2021-01-25"]
    _ = wapor_ts(bb, variable, period, overview)


def test_general_6(tmp_path):
    region = os.path.join(test_data_folder, "1237500.geojson")
    period = ["2021-01-12", "2021-01-25"]
    fp1 = wapor_map(region, "L2-AETI-D", period, tmp_path)
    ds = gdal.Open(fp1)
    assert ds.RasterCount == 2
    band = ds.GetRasterBand(1)
    ndv = band.GetNoDataValue()
    scale = band.GetScale()
    array = band.ReadAsArray() * scale
    array[array == ndv * scale] = np.nan
    mean = np.nanmean(array)
    md = band.GetMetadata()
    assert md == {
        "end_date": "2021-01-20",
        "long_name": "Actual EvapoTranspiration and Interception",
        "number_of_days": "10",
        "overview": "NONE",
        "start_date": "2021-01-11",
        "temporal_resolution": "Dekad",
        "units": "mm/day",
    }
    assert mean > 0.0
    assert mean < 15.0
    proj = osr.SpatialReference(wkt=ds.GetProjection())
    assert proj.GetAttrValue("AUTHORITY", 1) == "4326"
    ds = ds.FlushCache()

    fps1a = wapor_map(region, "L2-AETI-D", period, tmp_path, separate_unscale=True)
    ds = gdal.Open(fps1a[1])
    assert ds.RasterCount == 1
    band = ds.GetRasterBand(1)
    ndv = band.GetNoDataValue()
    scale = band.GetScale()
    assert scale == 1 or isinstance(scale, type(None))
    array_X = band.ReadAsArray()
    array_X[array_X == ndv] = np.nan
    mean_X = np.nanmean(array_X)

    ds_ = gdal.Open(fps1a[0])
    band_ = ds_.GetRasterBand(1)
    ndv_ = band_.GetNoDataValue()
    scale_ = band_.GetScale()
    assert scale_ == 1 or isinstance(scale_, type(None))
    array_ = band_.ReadAsArray()
    array_[array_ == ndv_] = np.nan
    mean_ = np.nanmean(array_)
    assert mean_ == mean  # NOTE mean comes from fp1 (without unscaling)
    md = band_.GetMetadata()
    assert md == {
        "end_date": "2021-01-20",
        "long_name": "Actual EvapoTranspiration and Interception",
        "number_of_days": "10",
        "overview": "NONE",
        "start_date": "2021-01-11",
        "temporal_resolution": "Dekad",
        "units": "mm/day",
    }
    assert mean_ > 0.0
    assert mean_ < 15.0
    proj = osr.SpatialReference(wkt=ds.GetProjection())
    assert proj.GetAttrValue("AUTHORITY", 1) == "4326"
    ds = ds.FlushCache()

    fps1b = wapor_map(
        region,
        "L2-AETI-D",
        period,
        tmp_path,
        unit_conversion="dekad",
        separate_unscale=True,
    )
    ds = gdal.Open(fps1b[1])
    assert ds.RasterCount == 1
    band = ds.GetRasterBand(1)
    ndv = band.GetNoDataValue()
    scale = band.GetScale()
    assert scale == 1 or isinstance(scale, type(None))
    array_Y = band.ReadAsArray()
    array_Y[array_Y == ndv] = np.nan
    mean_Y = np.nanmean(array_Y)
    md_Y = band.GetMetadata()
    assert mean_Y / int(md_Y["number_of_days"]) - mean_X < 1e-10


def test_general_7(tmp_path):
    region = os.path.join(test_data_folder, "1237500.geojson")
    period = ["2021-01-12", "2021-01-25"]
    fp2 = wapor_map(region, "L2-AETI-M", period, tmp_path)
    ds = gdal.Open(fp2)
    band = ds.GetRasterBand(1)
    md = band.GetMetadata()
    assert md["units"] == "mm/month"
    ds = ds.FlushCache()


def test_general_8(tmp_path):
    region = os.path.join(test_data_folder, "1237500.geojson")
    period = ["2021-01-12", "2021-01-25"]
    fp3 = wapor_map(region, "L2-AETI-A", period, tmp_path)
    ds = gdal.Open(fp3)
    band = ds.GetRasterBand(1)
    md = band.GetMetadata()
    assert md["units"] == "mm/year"
    ds = ds.FlushCache()


variables = [
    "L1-AETI-D",
    "L1-AETI-M",
    "L1-AETI-A",
]


@pytest.mark.parametrize("variable", variables)
def test_general_9(variable, tmp_path):
    region = os.path.join(test_data_folder, "1237500.geojson")
    period = ["2021-01-12", "2021-01-25"]
    _ = wapor_map(region, variable, period, tmp_path)


def test_general_10(tmp_path):
    bb = [25, -17, 26, -16]
    period = ["2021-01-12", "2021-01-25"]
    fp7 = wapor_map(bb, "L2-AETI-D", period, tmp_path)
    ds = gdal.Open(fp7)
    geot = ds.GetGeoTransform()
    nx = ds.RasterXSize
    ny = ds.RasterYSize
    assert bb[0] == geot[0]
    assert bb[2] == geot[0] + nx * geot[1]
    assert bb[1] == geot[3] + ny * geot[5]
    assert bb[3] == geot[3]
    band = ds.GetRasterBand(1)
    scale = band.GetScale()
    array = band.ReadAsArray() * scale
    ndv = band.GetNoDataValue()
    array[array == ndv * scale] = np.nan
    mean = np.nanmean(array)
    assert mean > 0.0
    assert mean < 15.0
    proj = osr.SpatialReference(wkt=ds.GetProjection())
    assert proj.GetAttrValue("AUTHORITY", 1) == "4326"
    ds = ds.FlushCache()


variables = [
    "L2-AETI-M",
    "L2-AETI-A",
    "L1-AETI-D",
    "L1-AETI-M",
    "L1-AETI-A",
]


@pytest.mark.parametrize("variable", variables)
def test_general_11(variable, tmp_path):
    bb = [25, -17, 26, -16]
    period = ["2021-01-12", "2021-01-25"]
    _ = wapor_map(bb, variable, period, tmp_path)


def test_general_12(tmp_path):
    region = os.path.join(test_data_folder, "1237500.geojson")
    period = ["2021-01-12", "2021-01-25"]
    fp13 = wapor_map(region, "L1-AETI-D", period, tmp_path, extension=".nc")
    info = gdal.Info(fp13, format="json")
    assert len(info["metadata"]["SUBDATASETS"]) == 4
    ds = gdal.Open(info["metadata"]["SUBDATASETS"]["SUBDATASET_1_NAME"])
    band = ds.GetRasterBand(1)
    scale = band.GetScale()
    array = band.ReadAsArray() * scale
    ndv = band.GetNoDataValue()
    array[array == ndv * scale] = np.nan
    mean = np.nanmean(array)
    assert mean > 0.0
    assert mean < 15.0
    proj = osr.SpatialReference(wkt=ds.GetProjection())
    assert proj.GetAttrValue("AUTHORITY", 1) == "4326"
    ds = ds.FlushCache()


def test_general_13(tmp_path):
    period = ["2021-01-12", "2021-01-25"]
    fp14 = wapor_map("BKA", "L3-T-D", period, tmp_path)
    ds = gdal.Open(fp14)
    proj = osr.SpatialReference(wkt=ds.GetProjection())
    assert proj.GetAttrValue("AUTHORITY", 1) == "32636"  # NOTE


def test_general_14(tmp_path):
    bbBKA = [35.75, 33.70, 35.82, 33.75]
    period = ["2021-01-12", "2021-01-25"]
    fp15 = wapor_map(bbBKA, "L3-T-D", period, tmp_path)
    assert "bb.BKA" in fp15
    ds = gdal.Open(fp15)
    band = ds.GetRasterBand(1)
    scale = band.GetScale()
    array = band.ReadAsArray() * scale
    ndv = band.GetNoDataValue()
    array[array == ndv * scale] = np.nan
    mean = np.nanmean(array)
    assert mean > 0.0
    assert mean < 15.0
    proj = osr.SpatialReference(wkt=ds.GetProjection())
    assert proj.GetAttrValue("AUTHORITY", 1) == "32636"
    ds = ds.FlushCache()


def test_general_15(tmp_path):
    period = ["2021-01-12", "2021-01-25"]
    region_bekaa = os.path.join(test_data_folder, "test_bekaa.geojson")
    _ = wapor_map(region_bekaa, "L1-T-D", period, tmp_path)


def test_general_16(tmp_path):
    period = ["2021-01-12", "2021-01-25"]
    region_GEZ = os.path.join(test_data_folder, "test_GEZ.geojson")
    _ = wapor_map(region_GEZ, "L3-T-D", period, tmp_path)


def test_general_17(tmp_path):
    period = ["2021-01-12", "2021-01-25"]
    region_GEZ = os.path.join(test_data_folder, "test_GEZ.geojson")
    GEZ = wapordl.bounding_boxes.L3_BBS.pop("GEZ")
    _ = wapor_map(region_GEZ, "L3-E-D", period, tmp_path)
    assert wapordl.bounding_boxes.L3_BBS.get("GEZ", None) == GEZ


def test_18(tmp_path):
    period = ["2021-01-12", "2021-01-25"]
    region_MUV = os.path.join(test_data_folder, "test_MUV_noCRS.geojson")
    _ = wapor_map(region_MUV, "L3-T-D", period, tmp_path)


def test_19(tmp_path):
    period = ["2021-01-12", "2021-01-25"]
    region_MULTIPLE = os.path.join(test_data_folder, "test_MULTIPLE.geojson")
    _ = wapor_map(region_MULTIPLE, "L3-T-D", period, tmp_path)


def test_20(tmp_path):
    period = ["2021-01-12", "2021-01-25"]
    region_3D = os.path.join(test_data_folder, "test_3D.geojson")
    _ = wapor_map(region_3D, "L1-T-D", period, tmp_path)
    _ = wapor_ts(region_3D, "L1-T-D", period, overview=2)


def test_21(tmp_path):
    period = ["2021-01-12", "2021-01-25"]
    region_not_4326 = os.path.join(test_data_folder, "test_MUV_UTM36N.geojson")
    _ = wapor_map(region_not_4326, "L1-T-D", period, tmp_path)


def test_22(tmp_path):
    period = ["2021-01-12", "2021-01-25"]
    region_noCRS = os.path.join(test_data_folder, "test_MUV_noCRS.geojson")
    _ = wapor_map(region_noCRS, "L1-T-D", period, tmp_path)


def test_23(tmp_path):
    period = ["2021-01-12", "2021-01-25"]
    region_shpfile = os.path.join(
        test_data_folder, "test_MUV_UTM36N_shp/test_MUV_UTM36N.shp"
    )
    _ = wapor_map(region_shpfile, "L1-T-D", period, tmp_path)

#####
# UNIT CONVERSION CHECKS
#####


def test_from_dekad():
    region = os.path.join(test_data_folder, "1237500.geojson")
    periodX = ["2021-01-01", "2021-01-31"]
    overview = 3

    # FROM DEKAD
    df_dekad_ref = wapor_ts(region, "L2-AETI-D", periodX, overview=overview)
    df_dekad_day = wapor_ts(
        region, "L2-AETI-D", periodX, overview=overview, unit_conversion="day"
    )
    assert df_dekad_day.attrs["units"] == "mm/day"
    assert np.all(df_dekad_ref["mean"] == df_dekad_day["mean"])
    df_dekad_dekad = wapor_ts(
        region, "L2-AETI-D", periodX, overview=overview, unit_conversion="dekad"
    )
    assert np.all(
        np.isclose(
            df_dekad_ref["mean"] * df_dekad_ref.number_of_days.dt.days,
            df_dekad_dekad["mean"],
            atol=0,
            rtol=1e-3,
        )
    )
    assert df_dekad_dekad.attrs["units"] == "mm/dekad"
    df_dekad_month = wapor_ts(
        region, "L2-AETI-D", periodX, overview=overview, unit_conversion="month"
    )
    assert np.all(
        np.isclose(df_dekad_ref["mean"] * 31, df_dekad_month["mean"], atol=0, rtol=1e-3)
    )
    assert df_dekad_month.attrs["units"] == "mm/month"
    df_dekad_year = wapor_ts(
        region, "L2-AETI-D", periodX, overview=overview, unit_conversion="year"
    )
    assert np.all(
        np.isclose(df_dekad_ref["mean"] * 365, df_dekad_year["mean"], atol=0, rtol=1e-3)
    )
    assert df_dekad_year.attrs["units"] == "mm/year"


def test_from_month():
    region = os.path.join(test_data_folder, "1237500.geojson")
    periodX = ["2021-01-01", "2021-01-31"]
    overview = 3

    df_month_ref = wapor_ts(region, "L2-AETI-M", periodX, overview=overview)
    df_month_day = wapor_ts(
        region, "L2-AETI-M", periodX, overview=overview, unit_conversion="day"
    )
    assert df_month_day.attrs["units"] == "mm/day"
    assert np.all(
        np.isclose(df_month_ref["mean"] / 31, df_month_day["mean"], atol=0, rtol=1e-2)
    )
    df_month_dekad = wapor_ts(
        region, "L2-AETI-M", periodX, overview=overview, unit_conversion="dekad"
    )
    assert np.all(
        np.isclose(df_month_ref["mean"] / 3, df_month_dekad["mean"], atol=0, rtol=1e-2)
    )
    assert df_month_dekad.attrs["units"] == "mm/dekad"
    df_month_month = wapor_ts(
        region, "L2-AETI-M", periodX, overview=overview, unit_conversion="month"
    )
    assert np.all(df_month_ref["mean"] == df_month_month["mean"])
    assert df_month_month.attrs["units"] == "mm/month"
    df_month_year = wapor_ts(
        region, "L2-AETI-M", periodX, overview=overview, unit_conversion="year"
    )
    assert np.all(
        np.isclose(df_month_ref["mean"] * 12, df_month_year["mean"], atol=0, rtol=1e-3)
    )
    assert df_month_year.attrs["units"] == "mm/year"


def test_from_year():
    region = os.path.join(test_data_folder, "1237500.geojson")
    periodX = ["2021-01-01", "2021-01-31"]
    overview = 3

    df_year_ref = wapor_ts(region, "L2-AETI-A", periodX, overview=overview)
    df_year_day = wapor_ts(
        region, "L2-AETI-A", periodX, overview=overview, unit_conversion="day"
    )
    assert df_year_day.attrs["units"] == "mm/day"
    assert np.all(
        np.isclose(df_year_ref["mean"] / 365, df_year_day["mean"], atol=0, rtol=1e-2)
    )
    df_year_dekad = wapor_ts(
        region, "L2-AETI-A", periodX, overview=overview, unit_conversion="dekad"
    )
    assert np.all(
        np.isclose(df_year_ref["mean"] / 36, df_year_dekad["mean"], atol=0, rtol=1e-2)
    )
    assert df_year_dekad.attrs["units"] == "mm/dekad"
    df_year_month = wapor_ts(
        region, "L2-AETI-A", periodX, overview=overview, unit_conversion="month"
    )
    assert np.all(
        np.isclose(df_year_ref["mean"] / 12, df_year_month["mean"], atol=0, rtol=1e-3)
    )
    assert df_year_month.attrs["units"] == "mm/month"
    df_year_year = wapor_ts(
        region, "L2-AETI-A", periodX, overview=overview, unit_conversion="year"
    )
    assert np.all(df_year_ref["mean"] == df_year_year["mean"])
    assert df_year_year.attrs["units"] == "mm/year"


def test_unit_conversion_1():
    region = os.path.join(test_data_folder, "1237500.geojson")
    periodX = ["2021-01-01", "2021-01-31"]
    overview = 3

    _ = wapor_ts(region, "L1-T-D", periodX, overview=overview, unit_conversion="dekad")
    df_npp_dekad_per_dekad = wapor_ts(
        region, "L1-NPP-D", periodX, overview=overview, unit_conversion="dekad"
    )
    assert np.all(df_npp_dekad_per_dekad["minimum"]) >= 0
    df_rsm_dekad_per_dekad = wapor_ts(
        region, "L1-RSM-D", periodX, overview=overview, unit_conversion="dekad"
    )
    assert np.all(df_rsm_dekad_per_dekad["minimum"]) >= 0.0
    assert np.all(df_rsm_dekad_per_dekad["maximum"]) <= 1.0


def test_unit_conversion_2(tmp_path):
    region = os.path.join(test_data_folder, "1237500.geojson")
    periodX = ["2021-01-01", "2021-01-31"]

    fp19 = wapor_map(region, "L2-AETI-D", periodX, tmp_path, unit_conversion="dekad")
    ds = gdal.Open(fp19)
    assert ds.RasterCount == 3
    band = ds.GetRasterBand(1)
    ndv = band.GetNoDataValue()
    scale = band.GetScale()
    assert not isinstance(scale, type(None))
    array = band.ReadAsArray() * scale
    array[array == ndv * scale] = np.nan
    mean = np.nanmean(array)
    md = band.GetMetadata()
    assert np.all(
        [
            md[k] == v
            for k, v in {
                "end_date": "2021-01-10",
                "long_name": "Actual EvapoTranspiration and Interception",
                "number_of_days": "10",
                "original_units": "mm/day",
                "overview": "NONE",
                "start_date": "2021-01-01",
                "temporal_resolution": "Dekad",
                "units": "mm/dekad",
                "units_conversion_factor": "10",
            }.items()
        ]
    )
    assert mean > 0.0
    assert mean < 25.0
    proj = osr.SpatialReference(wkt=ds.GetProjection())
    assert proj.GetAttrValue("AUTHORITY", 1) == "4326"
    ds = ds.FlushCache()


def test_unit_conversion_3(tmp_path):
    region = os.path.join(test_data_folder, "1237500.geojson")
    period = ["2021-01-12", "2021-01-25"]

    fp20 = wapor_map(
        region, "L2-AETI-D", period, tmp_path, extension=".nc", unit_conversion="dekad"
    )
    info = gdal.Info(fp20, format="json")
    assert len(info["metadata"]["SUBDATASETS"]) == 4
    ds = gdal.Open(info["metadata"]["SUBDATASETS"]["SUBDATASET_1_NAME"])
    band = ds.GetRasterBand(1)
    scale = band.GetScale()
    assert not isinstance(scale, type(None))
    array = band.ReadAsArray() * scale
    ndv = band.GetNoDataValue()
    array[array == ndv * scale] = np.nan
    mean = np.nanmean(array)
    assert mean > 0.0
    assert mean < 15.0
    proj = osr.SpatialReference(wkt=ds.GetProjection())
    assert proj.GetAttrValue("AUTHORITY", 1) == "4326"
    ds = ds.FlushCache()


if __name__ == "__main__":
    tmp_path = r"/Users/hmcoerver/Local/test"
