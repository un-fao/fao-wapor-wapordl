import logging
from typing import List

import requests


def check_urls(urls: List[str]) -> List[str]:
    """Check if URLS exist and filter out non-valid ones.

    Parameters
    ----------
    urls : List[str]
        ULRS to check.

    Returns
    -------
    List[str]
        URLS with non-valid ones filtered out.
    """
    for url in urls.copy():
        try:
            x = requests.get(url, stream=True)
            x.raise_for_status()
        except requests.exceptions.HTTPError:
            logging.debug(f"Invalid url detected, removing `{url}`.")
            urls.remove(url)
    return urls


def collect_responses(url: str, info: List[str] = ["code"]) -> list:
    """Calls GISMGR2.0 API and collects responses.

    Parameters
    ----------
    url : str
        URL to get.
    info : list, optional
        Used to filter the response, set to `None` to keep everything, by default `["code"]`.

    Returns
    -------
    list
        The responses.
    """
    data = {"links": [{"rel": "next", "href": url}]}
    output = list()
    while "next" in [x["rel"] for x in data["links"]]:
        url_ = [x["href"] for x in data["links"] if x["rel"] == "next"][0]
        response = requests.get(url_)
        response.raise_for_status()
        data = response.json()["response"]
        if isinstance(info, list) and "items" in data.keys():
            output += [tuple(x.get(y) for y in info) for x in data["items"]]
        elif "items" in data.keys():
            output += data["items"]
        else:
            output.append(data)
    if isinstance(info, list):
        try:
            output = sorted(output)
        except TypeError:
            output = output
    return output
