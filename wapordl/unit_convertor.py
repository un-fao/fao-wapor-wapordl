import importlib.util
import logging
from string import ascii_lowercase, ascii_uppercase

import pandas as pd
from osgeo import gdal, gdalconst
from osgeo_utils import gdal_calc

optional_packages = ["dask", "rioxarray", "xarray"]
use_xarray = all(
    [not isinstance(importlib.util.find_spec(x), type(None)) for x in optional_packages]
)
if use_xarray:
    import xarray as xr

def __make_band_names__(length):
    letters = [x for x in ascii_lowercase + ascii_uppercase]
    i = 2
    while len(letters) < length:
        for letter in letters[:52]:
            letters.append(letter * i)
        i += 1
    return letters[:length]


def unit_convertor(
    urls: list,
    in_fn: str,
    out_fn: str,
    unit_conversion: str,
    warp: gdal.Dataset,
    coptions=[],
) -> tuple:
    """Convert the units of multiple bands in a single geoTIFF file to another timescale.

    Parameters
    ----------
    urls : list
        Contains tuples of which the first item is a dictionary with metadata information for each band found in
        `in_fn`. Length of this list should be equal to the number of bands in `in_fn`.
    in_fn : str
        Path to geotiff file.
    out_fn : str
        Path to the to-be-created geotiff file.
    unit_conversion : str
        The desired temporal component of the converted units, should be one of
        "day", "dekad", "month" or "year".
    warp : gdal.Dataset
        The dataset to be adjusted, should point to `in_fn`.
    coptions : list, optional
        Extra creation options used to create `out_fn`, by default [].

    Returns
    -------
    tuple
        The new gdal.Dataset and the path to the created file.
    """

    global use_xarray

    input_files = dict()
    input_bands = dict()
    calc = list()
    should_convert = list()
    conversion_factors = list()
    letters = __make_band_names__(len(urls))

    if "AGERA5" in urls[0][1]:
        dtype = gdalconst.GDT_Float64
    else:
        dtype = gdalconst.GDT_Int32  # NOTE unit conversion can increase the DN's,
        # causing the data to not fit inside Int16 anymore...
        # so for now just moving up to Int32. Especially necessary
        # for NPP (which has a scale-factor of 0.001).

    for i, (md, _) in enumerate(urls):
        band_number = i + 1
        letter = letters[i]
        input_files[letter] = in_fn
        input_bands[f"{letter}_band"] = band_number
        if md.get("temporal_resolution", "unknown") == "Day":
            number_of_days = md.get("days_in_dekad", "unknown")
        else:
            number_of_days = md.get("number_of_days", "unknown")
        days_in_month = pd.Timestamp(md.get("start_date", "nat")).daysinmonth
        source_unit = md.get("units", "unknown")
        source_unit_split = source_unit.split("/")
        source_unit_q = "/".join(source_unit_split[:-1])
        source_unit_time = source_unit_split[-1]
        if any(
            [
                source_unit_time not in ["day", "month", "year", "dekad"],
                number_of_days == "unknown",
                source_unit == "unknown",
                pd.isnull(days_in_month),
            ]
        ):
            calc.append(f"{letter}.astype(numpy.float64)")
            md["units"] = source_unit
            md["units_conversion_factor"] = "N/A"
            md["original_units"] = "N/A"
            should_convert.append(False)
            conversion_factors.append(1)
        else:
            conversion = {
                ("day", "day"): 1,
                ("day", "dekad"): number_of_days,
                ("day", "month"): days_in_month,
                ("day", "year"): 365,
                ("dekad", "day"): 1 / number_of_days,
                ("dekad", "month"): 3,
                ("dekad", "year"): 36,
                ("dekad", "dekad"): 1,
                ("month", "day"): 1 / days_in_month,
                ("month", "dekad"): 1 / 3,
                ("month", "month"): 1,
                ("month", "year"): 12,
                ("year", "dekad"): 1 / 36,
                ("year", "day"): 1 / 365,
                ("year", "month"): 1 / 12,
                ("year", "year"): 1,
            }[(source_unit_time, unit_conversion)]
            calc.append(f"{letter}.astype(numpy.float64)*{conversion}")
            should_convert.append(True)
            conversion_factors.append(conversion)
            md["units"] = f"{source_unit_q}/{unit_conversion}"
            md["units_conversion_factor"] = conversion
            md["original_units"] = source_unit

    logging.debug(
        f"\ninput_files: {input_files}\ninput_bands: {input_bands}\ncalc: {calc}"
    )

    conversion_is_one = [x["units_conversion_factor"] == 1.0 for x, _ in urls]

    # NOTE See todo just below.
    scales = [warp.GetRasterBand(i + 1).GetScale() for i in range(warp.RasterCount)]
    offsets = [warp.GetRasterBand(i + 1).GetOffset() for i in range(warp.RasterCount)]

    logging.debug(f"\nSCALES: {scales}\nOFFSETS: {offsets}")

    if all(should_convert) and not all(conversion_is_one):
        logging.info(
            f"Converting units from [{source_unit}] to [{source_unit_q}/{unit_conversion}] (use_xarray = {use_xarray})."
        )

        ndv = warp.GetRasterBand(1).GetNoDataValue()
        if use_xarray:
            if "/vsi" not in in_fn:
                chunks = {"band": 1, "x": "auto", "y": "auto"}
            else:
                chunks = None
            ds = xr.open_dataset(
                in_fn,
                mask_and_scale=False,
                decode_coords="all",
                chunks=chunks,
            )
            xr_conv = xr.DataArray(conversion_factors, coords={"band": ds["band"]})
            ndv_ = ds["band_data"].attrs["_FillValue"]

            da = xr.where(
                ds["band_data"] == ndv_, ndv_, ds["band_data"] * xr_conv
            ).round(decimals=0)

            ds_out = da.to_dataset("band")
            for i, (scale, (md, _)) in enumerate(zip(scales, urls)):
                ds_out[i + 1].attrs = md
                ds_out[i + 1] = ds_out[i + 1].rio.write_nodata(ndv)
                ds_out[i + 1].attrs["scale_factor"] = scale

            ds_out = ds_out.rio.write_crs(ds.rio.crs)
            ds_out.rio.to_raster(
                out_fn,
                compress="LZW",
                dtype={5: "int32", 7: "float64"}[dtype],
                windowed=True,
                lock=True,
            )
            filen = out_fn
        else:
            logging.info(
                "Consider installing `xarray`, `rioxarray` and `dask` for faster unit conversions."
            )
            warp = gdal_calc.Calc(
                calc=calc,
                outfile=out_fn,
                overwrite=True,
                creation_options=coptions,
                quiet=True,
                type=dtype,
                NoDataValue=ndv,
                **input_files,
                **input_bands,
            )
            # TODO make bug report on GDAL for gdal_calc removing scale/offset factors
            for i, (scale, offset) in enumerate(zip(scales, offsets)):
                warp.GetRasterBand(i + 1).SetScale(scale)
                warp.GetRasterBand(i + 1).SetOffset(offset)
            warp.FlushCache()
            filen = out_fn
    else:
        if all(conversion_is_one):
            logging.info("Units are already as requested, no conversion needed.")
        else:
            logging.warning(
                "Couldn't succesfully determine unit conversion factors, keeping original units."
            )
        for i, (md, _) in enumerate(urls):
            if md["units_conversion_factor"] != "N/A":
                md["units"] = md["original_units"]
                md["units_conversion_factor"] = "N/A"
                md["original_units"] = "N/A"
        filen = in_fn

    return warp, filen
