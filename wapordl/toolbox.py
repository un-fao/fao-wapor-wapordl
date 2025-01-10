import os
from typing import List

import shapely
from osgeo import gdal, ogr


def get_area(fh: str, lyr_idx: int = 0, ftr_idx: int = 0) -> float:
    """Get the area of a geometry from a file, layer and feature index.

    Parameters
    ----------
    fh : str
        Patht to file.
    lyr_idx : int, optional
        Which layer index to use, by default 0.
    ftr_idx : int, optional
        Which feature index from the layer to use, by default 0.

    Returns
    -------
    float
        Area of the geometry.
    """
    ds = gdal.OpenEx(fh, gdal.OF_VECTOR)
    layer = ds.GetLayerByIndex(lyr_idx)
    ftr = list(layer)[ftr_idx]  # NOTE not ideal when there are a lot of features,
    # but that won't be the case here. Otherwise use
    # `ogr.Feature(layer.GetNextFeature())` instead.
    geom = ftr.GetGeometryRef()
    # geom = get_geom(fh, lyr_idx=lyr_idx, ftr_idx=ftr_idx)
    return geom.GetArea()


def get_bounds(fh: str, lyr_idx: int = 0, ftr_idx: int = 0) -> List[float]:
    """Get the bounds of a geometry as [left, right, bottom, top] from a file,
    layer and feature index.

    Parameters
    ----------
    fh : str
        Patht to file.
    lyr_idx : int, optional
        Which layer index to use, by default 0.
    ftr_idx : int, optional
        Which feature index from the layer to use, by default 0.

    Returns
    -------
    List[float]
        The bounds [left, right, bottom, top].
    """
    ds = gdal.OpenEx(fh, gdal.OF_VECTOR)
    layer = ds.GetLayerByIndex(lyr_idx)
    ftr = list(layer)[ftr_idx]  # NOTE not ideal when there are a lot of features,
    # but that won't be the case here. Otherwise use
    # `ogr.Feature(layer.GetNextFeature())` instead.
    geom = ftr.GetGeometryRef()
    bounds = geom.GetEnvelope()
    # NOTE returns xmin, ymin, xmax, ymax (!!!)
    return [bounds[0], bounds[2], bounds[1], bounds[3]]


def get_shapely(fh: str, lyr_idx: int = 0, ftr_idx: int = 0) -> shapely.Polygon:
    """Get a shapely object of a geometry from a file, layer and feature index.

    Parameters
    ----------
    fh : str
        Patht to file.
    lyr_idx : int, optional
        Which layer index to use, by default 0.
    ftr_idx : int, optional
        Which feature index from the layer to use, by default 0.

    Returns
    -------
    shapely.Polygon
        The shapely geometry object.
    """
    ds = gdal.OpenEx(fh, gdal.OF_VECTOR)
    layer = ds.GetLayerByIndex(lyr_idx)
    ftr = list(layer)[ftr_idx]  # NOTE not ideal when there are a lot of features,
    # but that won't be the case here. Otherwise use
    # `ogr.Feature(layer.GetNextFeature())` instead.
    geom = ftr.GetGeometryRef()
    return shapely.from_wkt(geom.ExportToWkt())


def check_vector(fh: str) -> tuple:
    """Check if a provided vector file is correctly formatted for wapordl.

    Parameters
    ----------
    fh : str
        Path to input file.

    Returns
    -------
    tuple
        Information about the input file, first value is EPSG code (int), second is
        driver name, third is True if coordinates are 2D.
    """
    # with ogr.Open(fh) as ds: # NOTE does not work in gdal < 3.7, so not using
    # for backward compatability with Colab.
    ds = ogr.Open(fh)

    driver = ds.GetDriver()
    layer = ds.GetLayer()
    ftr = layer.GetNextFeature()
    geom = ftr.geometry()
    is_two_d = geom.CoordinateDimension() == 2
    spatialRef = layer.GetSpatialRef()
    epsg = spatialRef.GetAuthorityCode(None)

    try:
        ds = ds.Close()
    except AttributeError as e:
        if str(e) == "'DataSource' object has no attribute 'Close'":
            ds = ds.Release()
        else:
            raise e

    return int(epsg), getattr(driver, "name", None), is_two_d



def reproject_vector(fh: str, epsg=4326, in_memory=False) -> str:
    """Create a 2D GeoJSON file with `EPSG:4326` SRS from any
    OGR compatible vector file.

    Parameters
    ----------
    fh : str
        Path to input file.
    epsg : int, optional
        target SRS, by default 4326.

    Returns
    -------
    str
        Path to output (GeoJSON) file.
    """

    ext = os.path.splitext(fh)[-1]
    out_fh = fh.replace(ext, f"_reprojected_{epsg}.geojson")

    if "/vsimem/" not in out_fh and in_memory:
        out_fh = "/vsimem/" + out_fh

    options = gdal.VectorTranslateOptions(
        dstSRS=f"EPSG:{epsg}",
        format="GeoJSON",
        dim="XY",
    )
    x = gdal.VectorTranslate(out_fh, fh, options=options)
    x.FlushCache()
    x = None

    return out_fh


def bb_to_vsimem(bb: List[float]) -> str:
    """Convert a bounding-box to a ogr vector stored in `/vsimem/`.

    Parameters
    ----------
    bb : List[float]
        Bounding-box as [xmin, ymin, xmax, ymax].

    Returns
    -------
    str
        Path to geojson object in `/vsimem/`.
    """
    bb_ = [str(x) for x in bb]
    coords = [
        (bb_[0], bb_[1]),
        (bb_[2], bb_[1]),
        (bb_[2], bb_[3]),
        (bb_[0], bb_[3]),
        (bb_[0], bb_[1]),
    ]
    merged_coords = ", ".join([" ".join(x) for x in coords])
    wkt = f"POLYGON (({merged_coords}))"

    geom = ogr.CreateGeometryFromWkt(wkt)
    outDriver = ogr.GetDriverByName("GeoJSON")
    fh = "/vsimem/test.geojson"
    outDataSource = outDriver.CreateDataSource(fh)
    outLayer = outDataSource.CreateLayer("temp", geom_type=ogr.wkbPolygon)
    featureDefn = outLayer.GetLayerDefn()
    outFeature = ogr.Feature(featureDefn)
    outFeature.SetGeometry(geom)
    outLayer.CreateFeature(outFeature)
    outFeature = None
    outDataSource = None

    return fh
