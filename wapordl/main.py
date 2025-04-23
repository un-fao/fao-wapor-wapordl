import logging
import os
from typing import List, Union

import numpy as np
import pandas as pd

import wapordl.products.agera5 as agera5
import wapordl.products.wapor3 as wapor3
import wapordl.toolbox.ogr_gdal as ogr_gdal
from wapordl.bounding_boxes import L2_BB, L3_BBS
from wapordl.overview_selector import determine_overview
from wapordl.region_selector import guess_l3_region, l3_bounding_boxes
from wapordl.variable_descriptions import collect_metadata, date_func


def wapor_dl(
    region: str | List[float] | None,
    variable: str,
    period: List[str] = ["2021-01-01", "2022-01-01"],
    overview: str | int = "NONE",
    unit_conversion: str = "none",
    folder: str | None = None,
    filename: str | None = None,
    max_error: float = 0.5,
    make_plots: bool | str = False,
    warp_kwargs: dict = {},
) -> Union[str, pd.DataFrame]:
    """Download a WaPOR or agERA5 variable for a specified region and period.

    Parameters
    ----------
    region : Union[str, List[float], None]
        Defines the area of interest. Can be a three letter code to describe a WaPOR level-3 region,
        a path to a vector or raster file or a list of 4 floats, specifying a bounding box.
    variable : str
        Name of the variable to download.
    period : list, optional
        Period for which to download data, by default ["2021-01-01", "2022-01-01"].
    overview : str | int, optional
        Select which overview from the COGs to use. Can be "NONE" or -1 to use the original data,
        an integer from 0 up to the total of overviews available or "AUTO" for
        automatic overview detection, by default "NONE".
    unit_conversion : str, optional
        Apply a unit conversion on the created file, can be one of "none", "day", "dekad",
        "month" or "year", by default "none".
    folder : str, optional
        Path to a folder in which to save any (intermediate) files. If set to `None`, everything will be
        kept in memory, by default None.
    filename : str, optional
        Set a different name for the output file, by default None.
    max_error : float, optional
        Only used when `overview` is set to `"AUTO"`, sets the error threshold, by default 0.5.
    make_plots : bool | str, optional
        Only used when `overview` is set to `"AUTO"`, create graphs showing the iteration process
        executed to determine the optimal overview. When a existing folder is defined, the graphs
        are saved into that folder as png files, by default False.
    warp_kwargs : dict, optional
        Additional gdal.Warp keyword arguments used when downloading data, by default {}.

    Returns
    -------
    Union[str, pd.DataFrame]
        Return a path to a file (if `req_stats` is `None`) or a pd.Dataframe if req_stats is a list
        speciyfing statistics.
    """

    global L3_BBS

    ## Retrieve info from variable name.
    level, _, tres = variable.split("-")

    vsimems = []

    ## Check if region is valid.
    # L3-CODE
    if all([isinstance(region, str), len(region) == 3]):
        if not region == region.upper():
            raise ValueError(
                f"Invalid region code `{region}`, region codes have three capitalized letters."
            )

        if region not in list(L3_BBS.keys()):
            logging.info(f"Searching bounding-box for `{region}`.")
            bb = l3_bounding_boxes(l3_region=region)
            if len(bb) == 0:
                raise ValueError(f"Unkown L3 region `{region}`.")
            else:
                logging.info(f"Bounding-box found for `{region}`.")
                L3_BBS = {**L3_BBS, **bb}

        if level == "L3":
            l3_region = region[:]  # three letter code to filter L3 datasets in GISMGR2.
            region = None  # used for clipping, can be None, list(bb) or path/to/file.geojson.
            region_code = l3_region[:]  # string to name the region in filenames etc.
            region_shape = None  # variable that can be passed to gdal.OpenEx(region_shape, gdal.OF_VECTOR)
        else:
            l3_region = None
            region_shape = ogr_gdal.to_vsimem(L3_BBS[region])
            vsimems.append(region_shape)
            region_code = region[:]
            region = ogr_gdal.get_bounds(
                region_shape, lrbt=False
            )  # list(region_shape.bounds)
    # GEOJSON
    elif isinstance(region, str) and ".tif" not in region:
        if "/vsicurl/" in region:
            region_code = "online_resource"
            region_shape = region
        elif not os.path.isfile(region):
            raise ValueError("Geojson file not found.")  # NOTE: TESTED
        else:
            region_code = os.path.split(region)[-1].replace(".geojson", "")
            epsg, driver, is_two_d = ogr_gdal.check_vector(region)
            if not np.all([epsg == 4326, driver == "GeoJSON", is_two_d]):
                ext_ = os.path.splitext(region)[-1]
                fn_ = os.path.split(region)[-1]
                out_fn_ = fn_.replace(ext_, "_reprojected.geojson")
                dim_ = {True: "2D", False: "3D"}[is_two_d]
                logging.warning(
                    f"Reprojecting `{fn_}` [EPSG:{epsg}, {dim_}] to `{out_fn_}` [EPSG:4326, 2D]."
                )
                region = ogr_gdal.reproject_vector(region, epsg=4326, in_memory=True)
                vsimems.append(region)
            region_shape = region

        l3_region = None
    # BB or BB_from_geotiff
    elif isinstance(region, list) or (isinstance(region, str) and ".tif" in region):
        if isinstance(region, str) and ".tif" in region:
            region = ogr_gdal.get_wgs84_bounds(region)

        if not all([region[2] > region[0], region[3] > region[1]]):
            raise ValueError("Invalid bounding box.")  # NOTE: TESTED
        else:
            region_code = "bb"
            region_shape = ogr_gdal.to_vsimem(bb=region)
            vsimems.append(region_shape)
        l3_region = None
    else:
        raise ValueError(f"Invalid value for region ({region}).")  # NOTE: TESTED

    ## Check l3_region code.
    if level == "L3" and isinstance(l3_region, type(None)):
        l3_region = guess_l3_region(region_shape)
        region_code += f".{l3_region}"

    ## Check the dates in period.
    if not isinstance(period, type(None)):
        period = [pd.Timestamp(x) for x in period]
        if period[0] > period[1]:
            raise ValueError("Invalid period.")  # NOTE: TESTED
        period = [x.strftime("%Y-%m-%d") for x in period]

    ## Collect urls for requested variable.
    if "AGERA5" in variable:
        urls = agera5.generate_urls(variable, period=period)
    else:
        urls = wapor3.generate_urls(variable, l3_region=l3_region, period=period)

    if len(urls) == 0:
        raise ValueError(
            "No files found for selected region, variable and period."
        )  # NOTE: TESTED

    ## Determine date for each url.
    md = collect_metadata(variable)
    md["overview"] = overview
    md_urls = [({**date_func(url, tres), **md}, url) for url in urls]

    logging.info(f"Found {len(md_urls)} files for {variable}.")

    # Determine overview
    if overview in ["auto", "AUTO"]:
        if isinstance(region, type(None)):
            logging.warning(
                "Determining an overview level for an entire L3 region is unsupported, setting overview to `'NONE'`."
            )
            overview = "NONE"
        elif isinstance(region, str) or isinstance(region, list):
            logging.info("Searching for optimal overview.")
            overview = determine_overview(
                md_urls[0][1], region, max_error=max_error, make_plots=make_plots
            )
            md_urls = [
                ({**md, **{"overview": f"AUTO:{overview}"}}, url) for md, url in md_urls
            ]
            logging.info(f"Using overview `{overview}`.")
        else:
            raise ValueError
    overview_ = -1 if overview == "NONE" else overview
    if overview not in [-1, "NONE"]:
        logging.warning("Downloading an overview instead of original data.")

    # Set gdal.Warp kwargs.
    info = ogr_gdal.get_info(md_urls[0][1])
    xres, yres = info["geoTransform"][1::4]
    warp_kwargs = {
        "xRes": abs(xres) * 2 ** (overview_ + 1),
        "yRes": abs(yres) * 2 ** (overview_ + 1),
        **warp_kwargs,
    }
    # BB | L3-code + L1/L2-variable (output = EPSG:4326)
    if isinstance(region, list):
        warp_kwargs["outputBounds"] = region
        warp_kwargs["outputBoundsSRS"] = "epsg:4326"
    # GEOJSON (output = EPSG:4326)
    elif isinstance(region, str):
        warp_kwargs["cutlineDSName"] = region
    # L3-code + L3-variable (output != EPSG:4326)
    elif isinstance(region, type(None)):
        ...
    else:
        ...

    ## Check if region overlaps with datasets bounding-box.
    if not isinstance(region_shape, type(None)) and level != "AGERA5":
        if level == "L2":
            bb_geom, bb_ftr = ogr_gdal.get_geom(L2_BB)[:2]
        else:
            data_bb_ = ogr_gdal.to_vsimem(coords=info["wgs84Extent"]["coordinates"][0])
            vsimems.append(data_bb_)
            bb_geom, bb_ftr = ogr_gdal.get_geom(data_bb_)[:2]
        region_geom, region_ftr = ogr_gdal.get_geom(region_shape)[:2]
        if not bb_geom.Intersects(region_geom):
            info_lbl1 = region_code if region_code != "bb" else str(region)
            info_lbl2 = (
                variable
                if isinstance(l3_region, type(None))
                else f"{variable}.{l3_region}"
            )
            raise ValueError(
                f"Selected region ({info_lbl1}) has no overlap with the datasets ({info_lbl2}) bounding-box."
            )
        del bb_ftr, region_ftr

    ## Determine output path.
    if folder:
        if not os.path.isdir(folder):
            os.makedirs(folder)
        if not isinstance(filename, type(None)):
            warp_fn = os.path.join(folder, f"{filename}.tif")
        else:
            overview__ = "NONE" if overview == -1 else overview
            warp_fn = os.path.join(
                folder, f"{region_code}_{variable}_{overview__}_{unit_conversion}.tif"
            )
    else:
        warp_fn = f"/vsimem/{pd.Timestamp.now()}_{region_code}_{variable}_{overview}_{unit_conversion}.tif"

    # Download the COG.
    warp_fn, vrt_fn = ogr_gdal.cog_dl(
        md_urls,
        warp_fn,
        overview=overview_,
        warp_kwargs=warp_kwargs,
        unit_conversion=unit_conversion,
    )
    # vsimems.append(warp_fn)
    vsimems.append(vrt_fn)

    ## Unlink memory files.
    ogr_gdal.unlink_vsimems(vsimems)

    return warp_fn


def wapor_map(
    region: Union[str, List[float], None],
    variable: str,
    period: List[str],
    folder: str,
    unit_conversion: str = "none",
    overview: str | int = "NONE",
    extension: str = ".tif",
    separate_unscale: bool = False,
    filename: str | None = None,
    max_error: float = 0.5,
    make_plots: bool | str = False,
    warp_kwargs: dict = {},
) -> str:
    """Download a map of a WaPOR3 or agERA5 variable for a specified region and period.

    Parameters
    ----------
    region : Union[str, List[float], None]
        Defines the area of interest. Can be a three letter code to describe a WaPOR level-3 region,
        a path to a vector file or a list of 4 floats, specifying a bounding box.
    variable : str
        Name of the variable to download.
    period : list
        Period for which to download data.
    folder : str
        Folder into which to download the data.
    unit_conversion : str, optional
        Apply a unit conversion on the created file, can be one of "none", "day", "dekad",
        "month" or "year", by default "none".
    overview : str | int, optional
        Select which overview from the COGs to use. Can be "NONE" or -1 to use the original data,
        an integer from 0 up to the total of overviews available or "AUTO" for
        automatic overview detection, by default "NONE".
    extension : str, optional
        One of ".tif" or ".nc", controls output format, by default ".tif".
    separate_unscale : bool, optional
        Set to `True` to create single band geotif files instead of a single geotif with multiple bands,
        does not do anything when extension is set to ".nc" , by default False.
    filename : str, optional
        Set a different name for the output file, by default None.
    max_error : float, optional
        Only used when `overview` is set to `"AUTO"`, sets the error threshold, by default 0.5.
    make_plots : bool | str, optional
        Only used when `overview` is set to `"AUTO"`, create graphs showing the iteration process
        executed to determine the optimal overview. When a existing folder is defined, the graphs
        are saved into that folder as png files, by default False.
    warp_kwargs : dict, optional
        Additional gdal.Warp keyword arguments used when downloading data, by default {}.

    Returns
    -------
    str
        Path to output file.
    """

    ## Check if a valid path to download into has been defined.
    if not os.path.isdir(folder):
        os.makedirs(folder)

    valid_units = ["none", "dekad", "day", "month", "year"]
    if unit_conversion not in valid_units:
        raise ValueError(
            f"Please select one of {valid_units} instead of {unit_conversion}."
        )  # NOTE: TESTED

    ## Call wapor_dl to create a GeoTIFF.
    fp = wapor_dl(
        region,
        variable,
        folder=folder,
        period=period,
        overview=overview,
        unit_conversion=unit_conversion,
        filename=filename,
        make_plots=make_plots,
        max_error=max_error,
        warp_kwargs=warp_kwargs,
    )

    fp = ogr_gdal.translate(fp, extension, separate_unscale=separate_unscale)

    ogr_gdal.unlink_vsimems(fp)

    return fp


def wapor_ts(
    region: Union[str, List[float], None],
    variable: str,
    period: List[str],
    identifier: str | None = None,
    n_threads: int = 1,
    overview: str | int = "NONE",
    unit_conversion: str = "none",
    max_error: float = 0.5,
    make_plots: bool | str = False,
    warp_kwargs: dict = {},
) -> pd.DataFrame:
    """Download a timeseries of a WaPOR3 or agERA5 variable for a specified region and period.

    Parameters
    ----------
    region : Union[str, List[float], None]
        Defines the area of interest. Can be a three letter code to describe a WaPOR level-3 region,
        a path to a vector file or a list of 4 floats, specifying a bounding box.
    variable : str
        Name of the variable to download.
    period : list
        Period for which to download data.
    identifier : str | None, optional
        Choose an attribute name contained in the `region` vector file to use when
        calculating zonal statistics in order to create multiple timeseries, by default None.
    n_threads : int, optional
        Specify how many threads to use when calculating zonal statistics, by default 1.
    overview : str | int, optional
        Select which overview from the COGs to use. Can be "NONE" or -1 to use the original data,
        an integer from 0 up to the total of overviews available or "AUTO" for
        automatic overview detection, by default "NONE".
    unit_conversion : str, optional
        Apply a unit conversion on the created file, can be one of "none", "day", "dekad",
        "month" or "year", by default "none".
    max_error : float, optional
        Only used when `overview` is set to `"AUTO"`, sets the error threshold, by default 0.5.
    make_plots : bool | str, optional
        Only used when `overview` is set to `"AUTO"`, create graphs showing the iteration process
        executed to determine the optimal overview. When a existing folder is defined, the graphs
        are saved into that folder as png files, by default False.
    warp_kwargs : dict, optional
        Additional gdal.Warp keyword arguments used when downloading data, by default {}.

    Returns
    -------
    pd.DataFrame
        Timeseries output.
    """

    valid_units = ["none", "dekad", "day", "month", "year"]
    if unit_conversion not in valid_units:
        raise ValueError(
            f"Please select one of {valid_units} instead of {unit_conversion}."
        )  # NOTE: TESTED

    ## Call wapor_dl to create a timeseries.
    fp = wapor_dl(
        region,
        variable,
        period=period,
        overview=overview,
        unit_conversion=unit_conversion,
        folder=None,
        max_error=max_error,
        make_plots=make_plots,
        warp_kwargs=warp_kwargs,
    )

    if all([isinstance(region, str), len(region) == 3]) or isinstance(region, list):
        if identifier is not None:
            logging.warning(
                "Using an identifier is only supported when using a vector as `region`, setting `identifier` to `None`."
            )
            identifier = None

    if identifier is None:
        df = ogr_gdal.get_stats(fp)
    else:
        df = ogr_gdal.zonal_stats(fp, region, identifier, n_threads=n_threads)

    ogr_gdal.unlink_vsimems(fp)

    return df


if __name__ == "__main__":
    ...
