from wapordl.main import (
    cog_dl,
    collect_metadata,
    date_func,
    generate_urls_v3,
    l3_codes,
    wapor_dl,
    wapor_map,
    wapor_ts,
)
from wapordl.overview_selector import determine_overview, geot_area
import logging
import requests

__all__ = [
    "cog_dl",
    "collect_metadata",
    "date_func",
    "generate_urls_v3",
    "l3_codes",
    "wapor_dl",
    "wapor_map",
    "wapor_ts",
    "determine_overview",
    "geot_area",
]
__version__ = "0.13.0"

logging.basicConfig(
    encoding="utf-8",
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    force=True,
)

def check_pywapor_version():
    """Check if the current version string is equal to
    the latest version available on pypi. If not, gives a
    warning.
    """
    package = "wapordl"
    logging.info(f"WaPORDL ({__version__}):")
    try:
        response = requests.get(f"https://pypi.org/pypi/{package}/json")
        response.raise_for_status()
    except Exception as _:
        ...
    else:
        latest_version = response.json()["info"]["version"]
        if latest_version != __version__:
            logging.warning(f"> Latest version is '{latest_version}'.")
            logging.warning("> Please update pywapor.")

check_pywapor_version()