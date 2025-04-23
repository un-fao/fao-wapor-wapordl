import concurrent.futures
import importlib.util
import logging
import os
import time
from functools import partial
from itertools import repeat
from typing import List, Tuple

import numpy as np
import pandas as pd
from osgeo import gdal, gdalconst, ogr, osr

from wapordl.unit_convertor import unit_convertor

optional_packages = ["tqdm"]
use_tqdm = all(
    [not isinstance(importlib.util.find_spec(x), type(None)) for x in optional_packages]
)
if use_tqdm:
    from tqdm import tqdm

gdal.UseExceptions()


def extension_in_gdal_drivers(extension, raise_error=False):
    succes = False
    for i in range(gdal.GetDriverCount()):
        drv = gdal.GetDriver(i)
        extensions = drv.GetMetadataItem(gdal.DMD_EXTENSIONS)
        # md = drv.GetMetadata_Dict()
        # shortname = drv.ShortName
        # longname = drv.LongName
        # is_raster = 'DCAP_RASTER' in md
        # is_vector = 'DCAP_VECTOR' in md
        if extensions is not None:
            if extension.replace(".", "") in extensions:
                succes = True
    guess = {
        ".nc": ("libgdal-netcdf", "netCDF"),
        ".jp2": ("libgdal-jp2openjpeg", "JP2OpenJPEG"),
    }
    if not succes:
        if extension in guess.keys():
            logging.warning(f"No driver found for `{guess[extension][1]}`.")
            logging.warning(
                f"Run `conda install -c conda-forge {guess[extension][0]}` to install a driver for `{guess[extension][1]}`."
            )
        else:
            logging.warning(f"No driver found for `{extension}`.")
        if raise_error:
            raise ValueError(
                f"No driver found for `{guess.get(extension, ['', extension])[1]}`."
            )
    return succes


_ = extension_in_gdal_drivers(".tif")
_ = extension_in_gdal_drivers(".nc")
_ = extension_in_gdal_drivers(".shp")
_ = extension_in_gdal_drivers(".geojson")
_ = extension_in_gdal_drivers(".gpkg")


def unlink_vsimems(paths):
    if not isinstance(paths, list):
        paths = [paths]
    for path in paths:
        if isinstance(path, str):
            if "/vsimem/" in path:
                try:
                    _ = gdal.Unlink(path)
                except RuntimeError:
                    ...


############
## RASTER ##
############


def cog_dl(
    urls: List[str],
    out_fn: str,
    overview: str | int = "NONE",
    warp_kwargs: dict = {},
    vrt_options: dict = {"separate": True},
    unit_conversion: str = "none",
) -> Tuple[str]:
    """Download multiple COGs into the bands of a single geotif or netcdf file.

    Parameters
    ----------
    urls : list
        URLs of the different COGs to be downloaded.
    out_fn : str
        Path to the output file.
    overview : str | int, optional
        Select which overview from the COGs to use. Can be "NONE" or -1 to use the original data,
        an integer from 0 up to the total of overviews available or "AUTO" for
        automatic overview detection, by default "NONE".
    warp_kwargs : dict, optional
        Additional gdal.Warp keyword arguments, by default {}.
    vrt_options : dict, optional
        Additional options passed to gdal.BuildVRT, by default {"separate": True}.
    unit_conversion : str, optional
        Apply a unit conversion on the created file, can be one of "none", "day", "dekad",
        "month" or "year", by default "none".

    Returns
    -------
    tuple
        Paths to the created geotiff file and the (intermediate) vrt file.

    Raises
    ------
    ValueError
        Invalid output extension selected.
    """
    global use_tqdm

    out_ext = os.path.splitext(out_fn)[-1]
    valid_ext = {".nc": "netCDF", ".tif": "GTiff"}
    valid_cos = {".nc": ["COMPRESS=DEFLATE", "FORMAT=NC4C"], ".tif": ["COMPRESS=LZW"]}
    if not bool(np.isin(out_ext, list(valid_ext.keys()))):
        raise ValueError(
            f"Please use one of {list(valid_ext.keys())} as extension for `out_fn`, not {out_ext}"
        )  # NOTE: TESTED
    vrt_fn = out_fn.replace(out_ext, ".vrt")

    ## Build VRT with all the required data.
    vrt_options_ = gdal.BuildVRTOptions(**vrt_options)
    prepend = {False: "/vsicurl/", True: "/vsigzip//vsicurl/"}
    vrt = gdal.BuildVRT(
        vrt_fn, [prepend[".gz" in x[1]] + x[1] for x in urls], options=vrt_options_
    )
    vrt.FlushCache()

    n_urls = len(urls)

    if use_tqdm:
        # Create waitbar.
        waitbar = tqdm(
            desc=f"Downloading {n_urls} COGs",
            leave=False,
            total=100,
            bar_format="{l_bar}{bar}|",
        )

        # Define callback function for waitbar progress.
        def _callback_func(info, *args):
            waitbar.update(info * 100 - waitbar.n)
    else:
        waitbar = _callback_func = None
        logging.info("Consider installing `tqdm` to display a download progress bar.")

    ## Download the data.
    warp_options = gdal.WarpOptions(
        format=valid_ext[out_ext],
        cropToCutline=True,
        overviewLevel=overview,
        multithread=True,
        targetAlignedPixels=True,
        creationOptions=valid_cos[out_ext],
        callback=_callback_func,
        warpOptions=["CUTLINE_ALL_TOUCHED", "TRUE"],
        **warp_kwargs,
    )
    warp = gdal.Warp(out_fn, vrt_fn, options=warp_options)
    warp.FlushCache()  # NOTE do not remove this.

    if waitbar is not None:
        waitbar.close()

    nbands = warp.RasterCount

    if nbands == n_urls and unit_conversion != "none":
        out_fn_new = out_fn.replace(out_ext, f"_converted{out_ext}")
        out_fn_old = out_fn
        warp, out_fn = unit_convertor(
            urls, out_fn, out_fn_new, unit_conversion, warp, coptions=valid_cos[out_ext]
        )
    else:
        out_fn_old = ""

    if nbands == n_urls:
        for i, (md, _) in enumerate(urls):
            if not isinstance(md, type(None)):
                band = warp.GetRasterBand(i + 1)
                band.SetDescription(md.get("start_date", f"Band {i + 1}"))
                band.SetMetadata(md)

    warp.FlushCache()

    if os.path.isfile(vrt_fn):
        try:
            os.remove(vrt_fn)
        except PermissionError:
            ...

    if os.path.isfile(out_fn_old) and os.path.isfile(out_fn_new):
        try:
            os.remove(out_fn_old)
        except PermissionError:
            ...

    return out_fn, vrt_fn


def get_stats(path: str) -> pd.DataFrame:
    """Get statistics for a raster file.

    Parameters
    ----------
    path : str
        Path to raster file.

    Returns
    -------
    pd.DataFrame
        The calculated statistics.
    """
    try:
        stats = gdal.Info(path, format="json", stats=True)
    except RuntimeError as e:
        if "Failed to compute statistics, no valid pixels found in sampling." in str(e):
            stats = gdal.Info(path, format="json", stats=False)
        else:
            raise e
    ## Get scale and offset factor.
    scale = stats["bands"][0].get("scale", 1)
    offset = stats["bands"][0].get("offset", 0)

    ## Check offset factor.
    if offset != 0:
        logging.warning("Offset factor is not zero, statistics might be wrong.")

    data = {
        statistic: [x.get(statistic, np.nan) for x in stats["bands"]]
        for statistic in ["minimum", "maximum", "mean"]
    }
    data: pd.DataFrame = pd.DataFrame(data) * scale
    data["start_date"] = [
        pd.Timestamp(x.get("metadata", {}).get("", {}).get("start_date", "nat"))
        for x in stats["bands"]
    ]
    data["end_date"] = [
        pd.Timestamp(x.get("metadata", {}).get("", {}).get("end_date", "nat"))
        for x in stats["bands"]
    ]
    data["number_of_days"] = [
        pd.Timedelta(
            float(x.get("metadata", {}).get("", {}).get("number_of_days", np.nan)),
            "days",
        )
        for x in stats["bands"]
    ]

    data.attrs = make_df_md(path)
    return data


def translate(
    fp: str, extension: str, separate_unscale: bool = False
) -> str | List[str]:
    """Change filetype of input raster.

    Parameters
    ----------
    fp : str
        Path to raster file to translate.
    extension : str
        Extension of output file, e.g. `".nc"`.
    separate_unscale : bool, optional
        Mutually exclusive with `extension=".tif"`. Creates multiple files with one band each, by default False.

    Returns
    -------
    str | List[str]
        Path to translated raster.
    """
    if extension == ".tif" and separate_unscale:
        logging.info("Splitting single GeoTIFF into multiple unscaled files.")
        ds = gdal.Open(fp)
        number_of_bands = ds.RasterCount
        fps = list()
        for band_number in range(1, number_of_bands + 1):
            band = ds.GetRasterBand(band_number)
            md = band.GetMetadata()
            options = gdal.TranslateOptions(
                unscale=True,
                outputType=gdalconst.GDT_Float64,
                bandList=[band_number],
                creationOptions=["COMPRESS=LZW"],
            )
            output_file = fp.replace(".tif", f"_{md['start_date']}.tif")
            x = gdal.Translate(output_file, fp, options=options)
            x.FlushCache()
            fps.append(output_file)
        ds.FlushCache()
        ds = None
        try:
            os.remove(fp)
        except PermissionError:
            ...
        return fps
    elif extension != ".tif":
        _ = extension_in_gdal_drivers(extension, raise_error=True)
        if separate_unscale:
            logging.warning(
                f"The `separate_unscale` option only works with `.tif` extension, not with `{extension}`."
            )
        logging.info(f"Converting from `.tif` to `{extension}`.")
        toptions = {".nc": {"creationOptions": ["COMPRESS=DEFLATE", "FORMAT=NC4C"]}}
        options = gdal.TranslateOptions(**toptions.get(extension, {}))
        new_fp = fp.replace(".tif", extension)
        ds = gdal.Translate(new_fp, fp, options=options)
        ds.FlushCache()
        try:
            os.remove(fp)
        except PermissionError:
            ...
        return new_fp
    else:
        return fp


def get_info(url: str) -> dict:
    """Get metadata from a online raster file.

    Parameters
    ----------
    url : str
        URL pointing to the raster file.

    Returns
    -------
    dict
        The metadata.
    """
    if not os.path.isfile(url):
        url = {False: "/vsicurl/", True: "/vsigzip//vsicurl/"}[".gz" in url] + url
    info = gdal.Info(url, format="json")
    return info


def get_extent(ds):
    """Return list of corner coordinates from a gdal Dataset"""
    xmin, xpixel, _, ymax, _, ypixel = ds.GetGeoTransform()
    width, height = ds.RasterXSize, ds.RasterYSize
    xmax = xmin + width * xpixel
    ymin = ymax + height * ypixel
    return (xmin, ymin), (xmax, ymax)


def reproject_coords(coords, src_srs, tgt_srs):
    """Reproject a list of x,y coordinates."""
    trans_coords = []
    transform = osr.CoordinateTransformation(src_srs, tgt_srs)
    for x, y in coords:
        x, y, z = transform.TransformPoint(x, y)
        trans_coords += [x]
        trans_coords += [y]
    return trans_coords


def get_wgs84_bounds(path):
    ds = gdal.Open(path)
    bounds = get_extent(ds)
    src_srs = osr.SpatialReference()
    src_srs.ImportFromWkt(ds.GetProjection())
    tgt_srs = osr.SpatialReference()
    tgt_srs.ImportFromEPSG(4326)
    trans_coords = reproject_coords(bounds, src_srs, tgt_srs)
    return trans_coords


############
## VECTOR ##
############


def get_geom(
    fh: str, lyr_idx: int = 0, ftr_idx: int = 0
) -> Tuple[ogr.Geometry, ogr.Feature, ogr.Layer, gdal.Dataset]:
    """_summary_

    Parameters
    ----------
    fh : str
        Path to vector file.
    lyr_idx : int, optional
        Index of layer to retrieve, by default 0.
    ftr_idx : int, optional
        Index of feature to retrieve, by default 0.

    Returns
    -------
    Tuple[ogr.Geometry, ogr.Feature, ogr.Layer, gdal.Dataset]
        The Geometry and other parts (Feature, Layer and Dataset) of the opened file.
        Make sure that the Feature stays open, otherwise the Geometry will be closed too.
    """
    ds = gdal.OpenEx(fh, gdal.OF_VECTOR)
    layer = ds.GetLayerByIndex(lyr_idx)
    for _ in range(ftr_idx + 1):
        ftr = layer.GetNextFeature()
    geom = ftr.GetGeometryRef()
    return geom, ftr, layer, ds  # NOTE need to return `ftr` to keep layer open.


def check_intersects(base_shape: str, bbs: dict) -> dict:
    """Check if a shape intersects with bounding-boxes stored in the values of a
    dictionary.

    Parameters
    ----------
    base_shape : str
        Path to vector.
    bbs : dict
        The bounding-boxes, keys are names, values are bounding-boxes.

    Returns
    -------
    dict
        Bool for every key/value pair in `bbs` indicating if the bounding-box intersects
        with `base_shape`.
    """
    geom, _ = get_geom(base_shape)[:2]
    checks = dict()
    for name, coords in bbs.items():
        wkt = coords_to_wkt_polygon(coords)
        geom_bb = ogr.CreateGeometryFromWkt(wkt)
        checks[name] = geom_bb.Intersects(geom)
    return checks


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
    geom, _ = get_geom(fh, lyr_idx=lyr_idx, ftr_idx=ftr_idx)[:2]
    return geom.GetArea()


def get_bounds(
    fh: str, lyr_idx: int = 0, ftr_idx: int = 0, lrbt: bool = True
) -> List[float]:
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
    geom, _ = get_geom(fh, lyr_idx=lyr_idx, ftr_idx=ftr_idx)[:2]
    bounds = geom.GetEnvelope()
    if lrbt:  # left right bottom top
        return [bounds[0], bounds[2], bounds[1], bounds[3]]
    else:
        return bounds


def get_wkt(fh: str, lyr_idx: int = 0, ftr_idx: int = 0) -> str:
    """Get a WKT string of a geometry from a file, layer and feature index.

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
    str
        The WKT string.
    """
    geom, _ = get_geom(fh, lyr_idx=lyr_idx, ftr_idx=ftr_idx)[:2]
    return geom.ExportToWkt()


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
    geom, _, layer, ds = get_geom(fh, lyr_idx=0, ftr_idx=0)

    driver = ds.GetDriver()
    driver_name = getattr(driver, "name", getattr(driver, "LongName", None))
    is_two_d = geom.CoordinateDimension() == 2
    spatialRef = layer.GetSpatialRef()
    epsg = spatialRef.GetAuthorityCode(None)

    try:
        ds = ds.Close()
    except AttributeError:
        ds = ds.FlushCache()

    return int(epsg), driver_name, is_two_d


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


def bb_to_coords(bb: list[float]) -> List[List[float]]:
    """Convert a bounding-box to a list of coordinates.

    Parameters
    ----------
    bb : List[float]
        Bounding-box as [xmin, ymin, xmax, ymax].

    Returns
    -------
    List[List[float]]
        The coordinates of the cornerpoints of the given bounding-box.
    """
    coords = [
        [bb[0], bb[1]],
        [bb[2], bb[1]],
        [bb[2], bb[3]],
        [bb[0], bb[3]],
        [bb[0], bb[1]],
    ]
    return coords


def coords_to_wkt_polygon(coords: list[float]) -> str:
    """Given a 2xN shaped list of coordinates, creates a WKT string.

    Parameters
    ----------
    coords : list[float]
        Coordinates to be converted.

    Returns
    -------
    str
        WKT string.
    """
    # Check if polygon is closed properly.
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    merged_coords = ", ".join([f"{x[0]} {x[1]}" for x in coords])
    wkt = f"POLYGON (({merged_coords}))"
    return wkt


def wkt_polygon_to_coords(wkt: str) -> List[List[float]]:
    """Convert a WKT string for a `POLYGON` into a list of coordinates.

    Parameters
    ----------
    wkt : str
        `POLYGON` WKT string.

    Returns
    -------
    List[List[float]]
        List of coordinates.

    Raises
    ------
    ValueError
        Raised when a non-`POLYGON` WKT string is passed.
    """
    wkt_type = wkt.split(" ")[0]
    if wkt_type != "POLYGON":
        raise ValueError(
            f"Only wkt with geometry type `POLYGON` supported, not `{wkt_type}`."
        )
    coords_ = wkt.replace("POLYGON ((", "").replace("))", "").split(",")
    coords = [[float(y) for y in x.split(" ")] for x in coords_]
    # Check if polygon is closed properly.
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords


def to_vsimem(bb: List[float] = None, coords: List[List[float]] = None) -> str:
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
    if bb is not None and coords is not None:
        raise ValueError  # TODO add test
    elif bb is not None:
        coords = bb_to_coords(bb)
    elif coords is not None:
        ...
    else:
        raise ValueError  # TODO add test

    wkt = coords_to_wkt_polygon(coords)

    geom = ogr.CreateGeometryFromWkt(wkt)
    outDriver = ogr.GetDriverByName("GeoJSON")
    fh = f"/vsimem/x_{time.strftime('%Y-%m-%d_%H%M%S')}_{np.random.randint(9999)}.geojson"
    outDataSource = outDriver.CreateDataSource(fh)
    outLayer = outDataSource.CreateLayer("temp", geom_type=ogr.wkbPolygon)
    featureDefn = outLayer.GetLayerDefn()
    outFeature = ogr.Feature(featureDefn)
    outFeature.SetGeometry(geom)
    outLayer.CreateFeature(outFeature)
    outFeature = None
    outDataSource = None

    return fh


#################
## ZONAL STATS ##
#################


def zone_stats(raster, vector, identifier, id_value):
    # Clip raster to the geometry.
    warp_options = gdal.WarpOptions(
        cutlineDSName=vector,
        cutlineWhere=f"\"{identifier}\"='{id_value}'",
        cropToCutline=True,
        # creationOptions=["COMPRESS=LZW"],
        warpOptions=["CUTLINE_ALL_TOUCHED", "TRUE"],
    )
    output_file = (
        f"/vsimem/x_{time.strftime('%Y-%m-%d_%H%M%S')}_{np.random.randint(9999)}.tif"
    )
    ds: gdal.Dataset = gdal.Warp(output_file, raster, options=warp_options)

    # Get statistics for the clipped dataset.
    data = get_stats(ds)
    data[identifier] = id_value

    # Unlink.
    unlink_vsimems(output_file)

    return data


def zonal_stats(
    raster: str | gdal.Dataset,
    vector: str,
    identifier: str,
    n_threads: int = 1,
):
    # Open the vector
    vector_ds: gdal.Dataset = gdal.OpenEx(vector, gdal.OF_VECTOR)

    # Check the number of layers.
    n_layers = vector_ds.GetLayerCount()
    if n_layers > 1:
        logging.warning(
            f"`{vector_ds}` has {n_layers} layers, only the first layer will be processed."
        )

    # Open the first layer.
    layer: ogr.Layer = vector_ds.GetLayer(0)

    # Check the geometry type.
    layer_def: ogr.FeatureDefn = layer.GetLayerDefn()
    geom_type = ogr.GeometryTypeToName(layer_def.GetGeomType())
    req_geom_type = ["Polygon", "Multi Polygon"]
    if geom_type not in req_geom_type:
        raise NotImplementedError(
            f"`zonal_stats` for geometry type `{geom_type}` has not been implemented. Use one of `{req_geom_type}`."
        )

    # Determine the field names.
    field_names = [
        getattr(layer_def.GetFieldDefn(x), "name")
        for x in range(layer_def.GetFieldCount())
    ]

    # Check if chosen ID is valid.
    if identifier not in field_names:
        raise ValueError(
            f"Identifier `{identifier}` not found in field names `{field_names}`."
        )

    # Determine ID values over which to loop.
    id_values = set([feature.GetField(identifier) for feature in layer])
    id_values.discard(None)  # NOTE: features without a ID value are skipped.

    # Calculate stats per ID value.
    if n_threads <= 1:
        data_parts = map(
            zone_stats, repeat(raster), repeat(vector), repeat(identifier), id_values
        )
    else:
        zone_stats_ = partial(zone_stats, raster, vector, identifier)
        executor = concurrent.futures.ThreadPoolExecutor(n_threads)
        futures = [executor.submit(zone_stats_, item) for item in id_values]
        concurrent.futures.wait(futures)
        data_parts = [x.result() for x in futures]

    # Merge everything.
    data: pd.DataFrame = (
        pd.concat(data_parts)
        .dropna()
        .sort_values([identifier, "start_date"])
        .reset_index(drop=True)
    )

    # Add metadata to pd.DataFrame.
    data.attrs = make_df_md(raster)

    return data


def make_df_md(raster, include=["long_name", "units", "overview", "original_units"]):
    info = gdal.Info(raster, format="json")
    try:
        md: dict = info["bands"][0]["metadata"][""]
        assert isinstance(md, dict)
    except (KeyError, IndexError, AssertionError):
        logging.warning("No valid metadata found.")
        md = {}
    df_md = {k: v for k, v in md.items() if k in include}
    return df_md


if __name__ == "__main__":
    ...
