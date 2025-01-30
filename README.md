![pip_downloads](https://img.shields.io/pypi/dw/wapordl?label=pip%7Cdownloads
) ![conda_downloads](https://img.shields.io/conda/d/conda-forge/wapordl) [![version](https://img.shields.io/pypi/v/wapordl?label=current%20version
)](https://anaconda.org/conda-forge/wapordl) ![min_python](https://img.shields.io/badge/python-%E2%89%A53.10-blue
)

# WaPORDL

Download data from the WaPOR3 dataset as spatially aggregated timeseries or as spatial data clipped to a bounding-box or shapefile.

## Installation

### Conda (recommended)
Install using conda by doing:

`conda install -c conda-forge wapordl`

### Pip (make sure GDAL is already installed in your environment)
To install with support for (1) faster unit conversions, (2) progress bars and (3) plotting do:

`pip install "wapordl[full]"`

Otherwise, the following suffices:

`pip install wapordl`

## Usage

To download a timeseries for a certain region:

```python
import wapordl

region = "test_data/test_MUV.geojson"
variable = "L2-AETI-D"
period = ["2021-01-01", "2021-07-01"]
overview = "AUTO" # set to "NONE" to use native resolution data.
# and check out examples/overviews.ipynb for a longer explanation
# of what this does.

df = wapordl.wapor_ts(region, variable, period, overview)

df

>>>     minimum  maximum    mean start_date   end_date number_of_days
>>> 0       0.7      3.0  2.3243 2021-01-01 2021-01-10        10 days
>>> 1       0.5      2.2  1.7202 2021-01-11 2021-01-20        10 days
>>> 2       0.9      3.7  2.9348 2021-01-21 2021-01-31        11 days
>>> ...
>>> 16      0.7      3.5  1.8653 2021-06-11 2021-06-20        10 days
>>> 17      0.8      4.1  1.9838 2021-06-21 2021-06-30        10 days
>>> 18      0.8      3.9  1.8965 2021-07-01 2021-07-10        10 days

df.attrs

>>> {'long_name': 'Actual EvapoTranspiration and Interception',
>>>  'units': 'mm/day',
>>>  'overview': 'AUTO:0'}
```

Variable names always consist of three parts defining; (1) the `level`, which can be one of `L1` (300m, global), `L2` (100m, Africa & Near East), `L3` (20m, regional) or `AGERA5` (0.1°, global); (2) the variable (e.g. ` AETI`) and; (3) the temporal resolution (`A` for annual, `M` for monthly, `D` for dekadal and `E` for daily). To see which variables are available, check `wapordl.variable_descriptions.WAPOR3_VARS` and `wapordl.variable_descriptions.AGERA5_VARS`, e.g.:

```python
wapordl.variable_descriptions.WAPOR3_VARS

>>> {
>>>     'L1-AETI-A': {'long_name': 'Actual EvapoTranspiration and Interception', 'units': 'mm/year'},
>>>     'L1-AETI-D': {'long_name': 'Actual EvapoTranspiration and Interception', 'units': 'mm/day'},
>>>     'L1-AETI-M': {'long_name': 'Actual EvapoTranspiration and Interception', 'units': 'mm/month'}
>>> ...
>>>     'L3-T-A': {'long_name': 'Transpiration', 'units': 'mm/year'},
>>>     'L3-T-D': {'long_name': 'Transpiration', 'units': 'mm/day'},
>>>     'L3-TBP-A': {'long_name': 'Total Biomass Production', 'units': 'kg/ha'}
>>> }
```

To download a timerseries and convert its unit provide the `unit_conversion` keyword:

```python
unit = "dekad" # or choose "day", "month", "year", "none" (default).

df = wapordl.wapor_ts(region, variable, period, overview = 3, unit_conversion = unit)

df

>>>     minimum  maximum    mean start_date   end_date number_of_days
>>> 0      16.0     26.0  23.6857 2021-01-01 2021-01-10        10 days
>>> 1      12.0     19.0  17.6286 2021-01-11 2021-01-20        10 days
>>> 2      23.1     36.3  32.6857 2021-01-21 2021-01-31        11 days
>>> ...
>>> 16     15.0     24.0  19.0857 2021-06-11 2021-06-20        10 days
>>> 17     16.0     27.0  20.2000 2021-06-21 2021-06-30        10 days
>>> 18     15.0     27.0  19.3143 2021-07-01 2021-07-10        10 days

df.attrs

>>> {'long_name': 'Actual EvapoTranspiration and Interception',
>>> 'units': 'mm/dekad',
>>> 'overview': 3,
>>> 'original_units': 'mm/day'}
```

To download a geotiff for a certain region and period of time:

```python
region = "path/to/some/my_region.geojson"
folder = "path/to/some/output/folder"
variable = "L2-AETI-D"
period = ["2021-01-01", "2021-07-01"]

fp = wapordl.wapor_map(region, variable, period, folder)

fp

>>> 'path/to/some/output/folder/my_region_L2-AETI-D_NONE_none.tif'
```

To save downloaded data in unscaled single-band files (instead of 1 file with multiple bands), set the `separate_unscale` keyword. Note that this will results in larger files.

```python
fps = wapordl.wapor_map(region, "L2-AETI-D", period, folder, separate_unscale = True)
```

To download a timeseries and a netcdf for a bounding-box:

```python
region = [35.75, 33.70, 35.82, 33.75] # [xmin, ymin, xmax, ymax]
folder = "path/to/some/output/folder"
variable = "L3-AETI-D"
period = ["2021-01-01", "2021-07-01"]
overview = "NONE"

df = wapordl.wapor_ts(region, variable, period, overview)
fp = wapordl.wapor_map(region, variable, period, folder, extension = ".nc")
```

An entire L3 region can be downloaded by specifying a three letter region code:
    
```python
region = "BKA"
folder = "path/to/some/output/folder"
variable = "L3-T-D"
period = ["2021-01-01", "2021-07-01"]
overview = 3

df = wapordl.wapor_ts(region, variable, period, overview)
fp = wapordl.wapor_map(region, variable, period, folder, unit_conversion = "year")
```

To get an overview of all the available L3 regions, run:

```python
wapordl.region_selector.l3_codes()

>>> {
>>>     'ERB': 'Erbil, Iraq',
>>>     'KAI': 'Kairouan, Tunisia',
>>>     'BKA': 'Bekaa, Lebanon',
>>> ...
>>>     'LOU': 'Moulay Bousselham, Morocco',
>>>     'ZAN': 'Zankalon, Egypt',
>>>     'MAG': 'Magdalena, Colombia'
>>> }
```

## Upcoming

- ~~Automatic overview selection based on the size and shape of the region.~~ ✅
- ~~Docstrings for all functions.~~ ✅
- ~~Option to split multiband GeoTIFF into single band files.~~ ✅
- ~~Support for variables with daily resolution (i.e. `L1-PCP-E` and `L1-RET-E`).~~ ✅
- ~~Easily download a lower level variable for a level-3 region.~~ ✅
- ~~Support for agERA5 variables.~~ ✅
- ~~Determine `l3_region` automatically from `region`.~~ ✅
- ~~Select unit of output.~~ ✅
- ~~Download a region from a bounding-box (i.e. without a shape).~~ ✅
- ~~A progress bar.~~ ✅
- ~~A warning if the given shape doesnt cover an area for which data is available.~~ ✅
- ~~Support for other output formats besides geotiff (e.g. netcdf).~~ ✅
- ~~Installation with conda.~~ ✅
- ~~More metadata in the output files.~~ ✅
- ~~More log information.~~ ✅
- ~~Option to select region for Level-3 data.~~ ✅

Got a feature-request or a question? Don't hesitate to contact me at [bert.coerver@fao.org](mailto:bert.coerver@fao.org) or open an [issue here](https://bitbucket.org/cioapps/wapordl/issues?status=new&status=open&status=submitted&is_spam=!spam).