import logging
import os

from osgeo import gdal

from wapordl.bounding_boxes import L3_BBS
from wapordl.toolbox import ogr_gdal
from wapordl.toolbox import query
from wapordl.products.wapor3 import generate_urls


def l3_bounding_boxes(variable="L3-T-A", l3_region=None) -> dict:
    """Determine the bounding-boxes of the WaPOR level-3 regions.

    Parameters
    ----------
    variable : str, optional
        Name of the variable used to check the bounding-box, by default "L3-T-A".
    l3_region : str, optional
        Name of the level-3 region to check, when `None` will check all available level-3 regions, by default None.

    Returns
    -------
    dict
        keys are three letter region codes, values are the coordinates of the bounding-boxes.
    """
    urls = generate_urls(
        variable, l3_region=l3_region, period=["2020-01-01", "2021-02-01"]
    )
    l3_bbs = {}
    for region_code, url in zip(
        [os.path.split(x)[-1].split(".")[-3] for x in urls], urls
    ):
        info = gdal.Info("/vsicurl/" + url, format="json")
        bb = info["wgs84Extent"]["coordinates"][0]
        l3_bbs[region_code] = bb
    return l3_bbs


def l3_codes() -> dict:
    """Create an overview of the available WaPOR level-3 region codes.

    Returns
    -------
    dict
        keys are three letter region codes, values are the long names of the region.
    """
    mapset_url = "https://data.apps.fao.org/gismgr/api/v2/catalog/workspaces/WAPOR-3/mosaicsets/L3-T-A/rasters?filter="
    x = query.collect_responses(mapset_url, info=["grid"])
    valids = {x_[0]["tile"]["code"]: x_[0]["tile"]["description"] for x_ in x}
    return valids


def update_L3_BBS():
    """Add bounding-boxes to the global `L3_BBS` in case they are not yet hard-coded,
    in case new areas have come online since the last WaPORDL release.

    Returns
    -------
    list
        list with three letter codes for new areas.
    """
    logging.info("Updating L3 bounding-boxes.")
    all_l3_regions = l3_codes()
    new_regions = set(all_l3_regions.keys()).difference(set(L3_BBS.keys()))
    added_regions = list()
    for l3_region in new_regions:
        new_bb = l3_bounding_boxes(l3_region=l3_region).get(l3_region, None)
        if not isinstance(new_bb, type(None)):
            added_regions.append(l3_region)
            L3_BBS[l3_region] = new_bb
    return added_regions


def guess_l3_region(region_shape: str) -> str:
    """_summary_

    Parameters
    ----------
    region_shape : str
        Path to vector.

    Returns
    -------
    str
        Three letter code identifying the WaPOR level-3 region.

    Raises
    ------
    ValueError
        Raised when the `region_shape` doesn't intersect with any level-3 region.
    """
    checks = ogr_gdal.check_intersects(region_shape, L3_BBS)

    number_of_results = sum(checks.values())

    if number_of_results == 0:
        added_regions = update_L3_BBS()
        l3_bbs = {x: L3_BBS[x] for x in added_regions}
        checks = ogr_gdal.check_intersects(region_shape, l3_bbs)
        number_of_results = sum(checks.values())
        if number_of_results == 0:
            raise ValueError(
                "`region` can't be linked to any L3 region."
            )  # NOTE: TESTED

    l3_regions = [k for k, v in checks.items() if v]
    l3_region = l3_regions[0]
    if number_of_results > 1:
        logging.warning(
            f"`region` intersects with multiple L3 regions ({l3_regions}), continuing with {l3_region} only."
        )
    else:
        logging.info(f"Given `region` matches with `{l3_region}` L3 region.")

    return l3_region


if __name__ == "__main__":
    ...
