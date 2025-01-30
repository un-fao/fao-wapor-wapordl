from typing import List, Tuple

from wapordl.toolbox.query import collect_responses


def generate_urls(
    variable: str, l3_region: str | None = None, period: List[str] | None = None
) -> Tuple[str]:
    """Find resource URLs for an agERA5 variable for a specified period.

    Parameters
    ----------
    variable : str
        Name of the variable.
    l3_region : str | None, optional
        Three letter code specifying the level-3 region, by default None.
    period : list, optional
        Start and end date in between which resource URLs will be searched, by default None.

    Returns
    -------
    tuple
        Resource URLs.

    Raises
    ------
    ValueError
        Invalid level selected.
    """

    level, _, _ = variable.split("-")

    if (level == "L1") or (level == "L2"):
        base_url = (
            "https://data.apps.fao.org/gismgr/api/v2/catalog/workspaces/WAPOR-3/mapsets"
        )
    elif level == "L3":
        base_url = "https://data.apps.fao.org/gismgr/api/v2/catalog/workspaces/WAPOR-3/mosaicsets"
    else:
        raise ValueError(f"Invalid level {level}.")  # NOTE: TESTED

    mapset_url = f"{base_url}/{variable}/rasters?filter="
    if not isinstance(l3_region, type(None)):
        mapset_url += f"code:CONTAINS:{l3_region};"
    if not isinstance(period, type(None)):
        mapset_url += f"time:OVERLAPS:{period[0]}:{period[1]};"

    urls = [x[0] for x in collect_responses(mapset_url, info=["downloadUrl"])]

    return tuple(sorted(urls))
