import logging

import requests

from wapordl.main import (
    wapor_dl,
    wapor_map,
    wapor_ts,
)

__all__ = [
    "wapor_dl",
    "wapor_map",
    "wapor_ts",
]
__version__ = "1.1.1"

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
    logging.info(f"WaPORDL (`{__version__}`)")
    try:
        response = requests.get(f"https://pypi.org/pypi/{package}/json")
        response.raise_for_status()
    except Exception as _:
        ...
    else:
        latest_version = response.json()["info"]["version"]
        if latest_version != __version__:
            # ...
            logging.warning(f"Latest version is '{latest_version}'.")
            logging.warning("Please update pywapor.")


check_pywapor_version()