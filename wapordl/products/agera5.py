import os
from typing import List, Tuple

import numpy as np
import pandas as pd

import wapordl.toolbox.query as query
from wapordl.variable_descriptions import AGERA5_VARS


def generate_urls(
    variable: str, period: List[str] | None = None, check_urls: bool = True
) -> Tuple[str]:
    """Find resource URLs for an agERA5 variable for a specified period.

    Parameters
    ----------
    variable : str
        Name of the variable.
    period : list, optional
        Start and end date in between which resource URLs will be searched, by default None.
    check_urls : bool, optional
        Perform additional checks to test if the found URLs are valid, by default True.

    Returns
    -------
    tuple
        Resource URLs.

    Raises
    ------
    ValueError
        Invalid variable selected.
    ValueError
        Invalid temporal resolution.

    Notes
    -----
    https://data.apps.fao.org/static/data/index.html?prefix=static%2Fdata%2Fc3s%2FMAPSET%2FAGERA5-ET0-D
    """
    level, var_code, tres = variable.split("-")

    if variable not in AGERA5_VARS.keys():
        raise ValueError(
            f"Invalid variable `{variable}`, choose one from `{AGERA5_VARS.keys()}`."
        )

    max_date = pd.Timestamp.now() - pd.Timedelta(days=25)
    if isinstance(period, type(None)):
        period = ["1979-01-01", max_date.strftime("%Y-%m-%d")]

    base_url = "https://data.apps.fao.org/static/data/c3s/MAPSET"
    urls = list()
    if tres == "E":
        x_filtered = make_daily_dates(period, max_date=max_date)
        for x in x_filtered:
            url = os.path.join(
                base_url,
                f"{level}-{var_code}",
                f"C3S.{level}-{var_code}.{x.strftime('%Y-%m-%d')}.tif",
            )
            urls.append(url)
    elif tres == "D":
        x_filtered = make_dekad_dates(period, max_date=max_date)
        for x in x_filtered:
            dekad = {1: 1, 11: 2, 21: 3}[x.day]
            url = os.path.join(
                base_url,
                variable,
                f"C3S.{variable}.{x.year}-{x.month:>02}-D{dekad}.tif",
            )
            urls.append(url)
    elif tres == "M":
        x_filtered = make_monthly_dates(period, max_date=max_date)
        for x in x_filtered:
            url = os.path.join(
                base_url, variable, f"C3S.{variable}.{x.year}-{x.month:>02}.tif"
            )
            urls.append(url)
    elif tres == "A":
        x_filtered = make_annual_dates(period, max_date=max_date)
        for x in x_filtered:
            url = os.path.join(base_url, variable, f"C3S.{variable}.{x.year}.tif")
            urls.append(url)
    else:
        raise ValueError(f"Invalid temporal resolution `{tres}`.")

    if check_urls:
        urls = query.check_urls(urls)

    return tuple(sorted(urls))


def make_dekad_dates(
    period: List[str], max_date: pd.Timestamp | None = None
) -> List[pd.Timestamp]:
    """Make a list of dekadal timestamps between a start and end date.

    Parameters
    ----------
    period : list
        Start and end date in between which the dekadal timestamps will be generated.
    max_date : pd.Timestamp, optional
        Choose the earliest date between the end of `period` and `max_date`, by default None.

    Returns
    -------
    list
        Dekadal timestamps between the given start and end date.
    """
    period_ = [pd.Timestamp(x) for x in period]
    if isinstance(max_date, pd.Timestamp):
        period_[1] = min(period_[1], max_date)
    syear = period_[0].year
    smonth = period_[0].month
    eyear = period_[1].year
    emonth = period_[1].month
    x1 = pd.date_range(f"{syear}-{smonth}-01", f"{eyear}-{emonth}-01", freq="MS")
    x2 = x1 + pd.Timedelta("10 days")
    x3 = x1 + pd.Timedelta("20 days")
    x = np.sort(np.concatenate((x1, x2, x3)))
    x_filtered = [pd.Timestamp(x_) for x_ in x if x_ >= period_[0] and x_ < period_[1]]
    return x_filtered


def make_monthly_dates(
    period: List[str], max_date: pd.Timestamp | None = None
) -> List[pd.Timestamp]:
    """Make a list of monthly timestamps between a start and end date.

    Parameters
    ----------
    period : list
        Start and end date in between which the monthly timestamps will be generated.
    max_date : pd.Timestamp, optional
        Choose the earliest date between the end of `period` and `max_date`, by default None.

    Returns
    -------
    list
        Monthly timestamps between the given start and end date.
    """
    period_ = [pd.Timestamp(x) for x in period]
    period_[0] = pd.Timestamp(f"{period_[0].year}-{period_[0].month}-01")
    if isinstance(max_date, pd.Timestamp):
        period_[1] = min(period_[1], max_date)
    x1 = pd.date_range(period_[0], period_[1], freq="MS")
    x_filtered = [pd.Timestamp(x_) for x_ in x1]
    return x_filtered


def make_annual_dates(
    period: List[str], max_date: pd.Timestamp | None = None
) -> List[pd.Timestamp]:
    """Make a list of annual timestamps between a start and end date.

    Parameters
    ----------
    period : list
        Start and end date in between which the annual timestamps will be generated.
    max_date : pd.Timestamp, optional
        Choose the earliest date between the end of `period` and `max_date`, by default None.

    Returns
    -------
    list
        Annual timestamps between the given start and end date.
    """
    period_ = [pd.Timestamp(x) for x in period]
    period_[0] = pd.Timestamp(f"{period_[0].year}-01-01")
    if isinstance(max_date, pd.Timestamp):
        period_[1] = min(period_[1], max_date)
    try:
        x1 = pd.date_range(period_[0], period_[1], freq="YE-JAN")
    except ValueError as e:
        if "Invalid frequency: YE-JAN" in str(e):
            x1 = pd.date_range(period_[0], period_[1], freq="A-JAN")
        else: 
            raise(e)
    x_filtered = [pd.Timestamp(x_) for x_ in x1]
    return x_filtered


def make_daily_dates(
    period: List[str], max_date: pd.Timestamp | None = None
) -> List[pd.Timestamp]:
    """Make a list of daily timestamps between a start and end date.

    Parameters
    ----------
    period : list
        Start and end date in between which the daily timestamps will be generated.
    max_date : pd.Timestamp, optional
        Choose the earliest date between the end of `period` and `max_date`, by default None.

    Returns
    -------
    list
        Daily timestamps between the given start and end date.
    """
    period_ = [pd.Timestamp(x) for x in period]
    if isinstance(max_date, pd.Timestamp):
        period_[1] = min(period_[1], max_date)
    x1 = pd.date_range(period_[0], period_[1], freq="D")
    x_filtered = [pd.Timestamp(x_) for x_ in x1]
    return x_filtered
