import glob
import os
import logging
import shapely.plotting
# import wapordl.main

import matplotlib.pyplot as plt
import numpy as np
from osgeo import gdal, ogr

gdal.UseExceptions()


def reproject_vector(fh: str, epsg=4326, in_memory=True) -> str:
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
    out_fh = fh.replace(ext, f"_reprojected{epsg}.geojson")

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

def bb_to_vsimem(bb) -> str:

    bb_ = [str(x) for x in bb]
    coords = [
        (bb_[0], bb_[1]),
        (bb_[2], bb_[1]),
        (bb_[2], bb_[3]),
        (bb_[0], bb_[3]),
        (bb_[0], bb_[1]),
    ]
    merged_coords = ", ".join([" ".join(x) for x in coords])
    wkt = f'POLYGON (({merged_coords}))'

    geom = ogr.CreateGeometryFromWkt(wkt)
    outDriver = ogr.GetDriverByName('GeoJSON')
    fh = "/vsimem/test.geojson"
    outDataSource = outDriver.CreateDataSource(fh)
    outLayer = outDataSource.CreateLayer('temp', geom_type=ogr.wkbPolygon)
    featureDefn = outLayer.GetLayerDefn()
    outFeature = ogr.Feature(featureDefn)
    outFeature.SetGeometry(geom)
    outLayer.CreateFeature(outFeature)
    outFeature = None
    outDataSource = None

    return fh

def geot_area(shape_fh: str, geot: list, zero_is_nan=True, make_plots=False) -> float:
    
    # Get the bounding-box of the shape
    bounds = get_bounds(shape_fh)
    coords = np.array(bounds).reshape((2, 2))

    # List which pixels intersect with the bb.
    nx_ny = np.array(
        [
            np.floor((coords[:, 0] - geot[0]) / geot[1]),
            np.ceil((coords[:, 1] - geot[3]) / abs(geot[5])),
        ]
    ).T

    # Snap the bounding-box to the geot.
    bounds = np.array(
        [
            geot[0] + nx_ny[0, 0] * geot[1],
            geot[3] + (nx_ny[0, 1] - 1) * abs(geot[5]),
            geot[0] + (nx_ny[-1, 0] + 1) * geot[1],
            geot[3] + nx_ny[-1, 1] * abs(geot[5]),
        ]
    ).T

    # Allow in-memory files (required for GDAL>=3.10)
    gdal_config_options = {"GDAL_MEM_ENABLE_OPEN": "YES"}

    # Set Rasterize options.
    rast_options = gdal.RasterizeOptions(
        burnValues=1,
        outputBounds=bounds,
        xRes=geot[1],
        yRes=geot[1],
        format="MEM",
        # allTouched=True,
    )

    # Make an array with 0=outside shape and 1=inside shape.
    try:
        for k, v in gdal_config_options.items():
            gdal.SetConfigOption(k, v)
        x = gdal.Rasterize("", shape_fh, options=rast_options)
    except Exception as e:
        raise e
    finally:
        for k, v in gdal_config_options.items():
            gdal.SetConfigOption(k, None)

    # Determine the area of the rasterizs shape.
    band = x.GetRasterBand(1)
    array = band.ReadAsArray()
    array[array == 0.0] = np.nan
    area = np.nansum(array) * geot[1] ** 2

    # Set to nan if requested.
    if zero_is_nan and area == 0.0:
        area = np.nan

    if make_plots and area not in [0.0, np.nan]:
        fig = plt.figure()
        ax = fig.gca()

        ax.imshow(
            array,
            cmap="tab10",
            extent=[bounds[0], bounds[2], bounds[1], bounds[3]],
            zorder=0,
        )

        shape = get_shapely(shape_fh)
        _ = shapely.plotting.plot_polygon(
            shapely.unary_union(shape),
            ax=ax,
            add_points=True,
            color="tab:red",
            zorder=10,
        )

        xticks_minor = np.arange(bounds[0], bounds[2], geot[1])
        xticks = np.arange(
            bounds[0] + 0.5 * geot[1], bounds[2] - 0.5 * geot[1], 3 * geot[1]
        )
        ax.set_xticks(xticks_minor, minor=True)
        ax.set_xticks(xticks)
        yticks_minor = np.arange(bounds[1], bounds[3], geot[1])
        yticks = np.arange(
            bounds[1] + 0.5 * geot[1], bounds[3] - 0.5 * geot[1], 3 * geot[1]
        )
        ax.set_yticks(yticks_minor, minor=True)
        ax.set_yticks(yticks)
        ax.grid(which="minor", color="w", linestyle=":", linewidth=1)

        ax.set_facecolor("lightgray")
        ax.set_xlabel("longitude [DD]")
        ax.set_ylabel("latitude [DD]")
        ax.set_title(f"FILE = {os.path.split(shape_fh)[-1]} \n\n PIXELSIZE = {geot[1]}")
        ax.tick_params(which="minor", bottom=False, left=False)

        if os.path.isdir(make_plots):
            plot_fh = os.path.join(make_plots, f"{area}_{os.path.split(shape_fh)[-1].replace('.geojson', '')}.png")
            fig.savefig(plot_fh)

    return area


def get_area(fh, lyr_idx = 0, ftr_idx = 0):
    ds = gdal.OpenEx(fh, gdal.OF_VECTOR)
    layer = ds.GetLayerByIndex(lyr_idx)
    ftr = list(layer)[ftr_idx]
    geom = ftr.GetGeometryRef()
    area = geom.GetArea()
    return area

def get_bounds(fh, lyr_idx = 0, ftr_idx = 0):
    ds = gdal.OpenEx(fh, gdal.OF_VECTOR)
    layer = ds.GetLayerByIndex(lyr_idx)
    ftr = list(layer)[ftr_idx]
    geom = ftr.GetGeometryRef()
    bounds = geom.GetEnvelope()
    return [bounds[0], bounds[2], bounds[1], bounds[3]]

def get_shapely(fh, lyr_idx = 0, ftr_idx = 0):
    ds = gdal.OpenEx(fh, gdal.OF_VECTOR)
    layer = ds.GetLayerByIndex(lyr_idx)
    ftr = list(layer)[ftr_idx]
    geom = ftr.GetGeometryRef()
    return shapely.from_wkt(geom.ExportToWkt())

def determine_overview(info_fh, shape_fh, max_error=0.5, make_plots=False):
    
    # Load raster information.
    info = gdal.Info(info_fh, format="json")
    epsg = int(info["coordinateSystem"]["wkt"].split('ID["EPSG",')[-1][:-2])
    
    if isinstance(shape_fh, list):
        shape_fh = bb_to_vsimem(shape_fh)
    if epsg != 4326:
        shape_fh = reproject_vector(shape_fh, epsg=epsg)

    shape_area = get_area(shape_fh)

    # Determine the scales to convert the original geot.
    res = np.array(info["size"])
    overview_scales = {
        i: np.round(res / np.array(x["size"]))
        for i, x in enumerate(info["bands"][0]["overviews"])
    }
    overview_scales[-1] = np.array([1.0, 1.0])

    # Variables to store outputs.
    errors = list()
    overviews = list()

    # Loop over the outputs, starting with the coarsest.
    for overview, scales in sorted(overview_scales.items(), reverse=True):
        # Make overview geotransform.
        geot = info["geoTransform"] * np.array([1, scales[0], 1, 1, 1, scales[1]])
        # Determine the area of the pixels overlapping with the shape.
        outline_area = geot_area(shape_fh, geot, make_plots=make_plots)
        # Calculate the relative difference in area.
        error = abs(1 - (shape_area / outline_area)) * 100
        # Store outputs.
        errors.append(error)
        overviews.append(overview)
        # Stop when the error is below the threshold.
        if errors[-1] < max_error:
            break
        # Stop when the error doesn't decrease anymore.
        if len(errors) > 2:
            if errors[-3] - errors[-1] == 0.0:
                logging.info("Search converged.")
                break

    # Select the overview with the smallest error.
    if all(np.isnan(errors)):
        overview = -1
    else: 
        overview = overviews[np.nanargmin(errors)]

    # Create a plot if necessary.
    if make_plots:
        fig = plt.figure()
        ax = fig.gca()
        if len(errors) >= 2:
            ax.plot(
                overviews[: len(errors)],
                np.gradient(np.array(errors)),
                marker="*",
                color="tab:red",
                linestyle=":",
                label="gradient of error",
            )
        ax.plot(
            overviews[: len(errors)],
            np.array(errors),
            marker="o",
            color="tab:red",
            label="error",
        )
        ax.axhline(
            y=max_error, color="k", linestyle=":", label=f"max error = {max_error}"
        )
        ax.set_xlim([-2, max(overviews) + 1])
        ax.grid()
        ax.set_facecolor("lightgray")
        ax.set_xlabel("overview [-]")
        ax.set_ylabel("error [-]")
        ax.set_title(
            f"FILE = {os.path.split(shape_fh)[-1]} \n\n SELECTED OVERVIEW = {overview} \n\n GEOT = {info['geoTransform']}"
        )
        fig.legend()

        if os.path.isdir(make_plots):
            plot_fh = os.path.join(make_plots, f"{overview}_{os.path.split(shape_fh)[-1].replace('.geojson', '')}.png")
            fig.savefig(plot_fh)

    return overview


if __name__ == "__main__":
    region = "BKA"
    variable = "L1-T-D"
    period = ["2021-01-01", "2021-01-01"]
    overview = -1
    folder = "/Users/hmcoerver/Local/auto_detect"
    lyr_idx = 0
    ftr_idx = 0

    shape_fhs = glob.glob(r"/Users/hmcoerver/Library/Mobile Documents/com~apple~CloudDocs/GitHub/wapordl/wapordl/test_data/detector_shapes/*.geojson")
    i = 2
    shape_fh = shape_fhs[i]
    # shape_fh = "/Users/hmcoerver/Library/Mobile Documents/com~apple~CloudDocs/GitHub/wapordl/wapordl/test_data/test_MUV.geojson"
    shape_fh = "/Users/hmcoerver/Library/Mobile Documents/com~apple~CloudDocs/GitHub/wapordl/wapordl/test_data/detector_shapes/star.geojson"
    bb = get_bounds(shape_fh)


    # info_fh = "/vsicurl/https://storage.googleapis.com/fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-AETI-D/WAPOR-3.L3-AETI-D.MUV.2021-01-D1.tif"
    info_fh = "/vsicurl/https://storage.googleapis.com/fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-T-D/WAPOR-3.L1-T-D.2021-01-D1.tif"

    overview = determine_overview(info_fh, shape_fh, make_plots=True, max_error = 0.5)

    # print(shape_fh, overview)

    # # Below is purely for debugging/development, should not be used in final solution.
    # # grid = make_grid(shape, geot_)

    # # geot = [-180.0, 0.0029296875, 0.0, 90.0, 0.0, -0.0029296875]
    # # shape_fh = '/Users/hmcoerver/Local/auto_detect/test_shapes/star.geojson'
    # test_fh = wapordl.wapor_map(shape_fh, variable, period, folder, overview=overview)
