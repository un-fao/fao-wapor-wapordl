import importlib.util
import logging
import os
from typing import List

import numpy as np
from osgeo import gdal

import wapordl.toolbox.ogr_gdal as ogr_gdal

optional_packages = ["matplotlib"]
use_plt = all(
    [not isinstance(importlib.util.find_spec(x), type(None)) for x in optional_packages]
)
if use_plt:
    import matplotlib.patches
    import matplotlib.pyplot as plt

gdal.UseExceptions()


def geot_area(
    shape_fh: str,
    geot: List[float],
    zero_is_nan: bool = True,
    make_plots: bool | str = False,
) -> float:
    """Given a shape and a geotransform, this functions calculates the area of the pixels
    that would cover the shape.

    Parameters
    ----------
    shape_fh : str
        Path to a vector-file than can be opened by `gdal.OpenEx`.
    geot : List[float]
        A geotransform describing the locations of pixels of a raster.
    zero_is_nan : bool, optional
        Set the output to `np.nan` if the resulting area is zero, by default True.
    make_plots : bool | str, optional
        Create a plot visualising the shape and the overlapping raster. If a path to an existing
        folder is given, the plot is saved as a png file, by default False.

    Returns
    -------
    float
        Area of the pixels that would overlap with the shape.
    """
    global use_plt

    # Get the bounding-box of the shape
    bounds = ogr_gdal.get_bounds(shape_fh)
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

    if make_plots and not use_plt:
        logging.info(
            "Unable to create plots without `matplotlib`, consider installing it or setting `make_plots=False`."
        )
    elif make_plots and area not in [0.0, np.nan] and use_plt:
        fig = plt.figure()
        ax = fig.gca()

        ax.imshow(
            array,
            cmap="tab10",
            extent=[bounds[0], bounds[2], bounds[1], bounds[3]],
            zorder=0,
        )

        geom, _ = ogr_gdal.get_geom(shape_fh)[:2]
        wkt = geom.UnaryUnion().ExportToWkt()
        coords = ogr_gdal.wkt_polygon_to_coords(wkt)
        shape_patch = matplotlib.patches.Polygon(
            coords,
            color="tab:red",
            zorder=10,
            alpha=0.4,
        )
        ax.add_patch(shape_patch)

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
            plot_fh = os.path.join(
                make_plots,
                f"{area}_{os.path.split(shape_fh)[-1].replace('.geojson', '')}.png",
            )
            fig.savefig(plot_fh)
    else:
        ...

    return area


def determine_overview(
    info_fh: str,
    shape_fh: str | List[float],
    max_error: float = 0.5,
    make_plots: bool | str = False,
) -> int:
    """Given a raster file, iterates over the geotransforms of the raster and any
    overviews present and checks how well the pixels are able to represent a given shape.

    Parameters
    ----------
    info_fh : str
        Path to a raster file.
    shape_fh : str | List[float]
        Path to a vector file or a list describing a bounding-box as
        [xmin, ymin, xmax, ymax].
    max_error : float, optional
        Threshold for the iteration, by default 0.5.
    make_plots : bool | str, optional
        Create graphs showing the iteration process executed to determine the
        optimal overview. When an existing folder is defined, the graphs
        are saved into that folder as png files, by default False.

    Returns
    -------
    int
        The selected overview.
    """
    global use_plt

    # Load raster information.
    info = ogr_gdal.get_info(info_fh)
    epsg = int(info["coordinateSystem"]["wkt"].split('ID["EPSG",')[-1][:-2])

    if isinstance(shape_fh, list):
        shape_fh = ogr_gdal.to_vsimem(bb=shape_fh)
    if epsg != 4326:
        shape_fh = ogr_gdal.reproject_vector(shape_fh, epsg=epsg, in_memory=True)

    shape_area = ogr_gdal.get_area(shape_fh)

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

    ogr_gdal.unlink_vsimems(shape_fh)

    # Create a plot if necessary.
    if make_plots and not use_plt:
        logging.info(
            "Unable to create plots without `matplotlib`, consider installing it or setting `make_plots=False`."
        )
    elif make_plots and use_plt:
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
            plot_fh = os.path.join(
                make_plots,
                f"{overview}_{os.path.split(shape_fh)[-1].replace('.geojson', '')}.png",
            )
            fig.savefig(plot_fh)
    else:
        ...

    return overview


if __name__ == "__main__":
    ...
