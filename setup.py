from setuptools import find_packages, setup

setup(
    name="wapordl",
    version="1.1.1",
    packages=find_packages(include=["wapordl", "wapordl.*"]),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        # "libgdal-netcdf", # conda-forge
        "requests",
        "pandas>=2.1.0,<3",
        "numpy>=1.15,<3",
        "gdal>=3.6.4,<4",
    ],
    extras_require={"full": ["xarray", "rioxarray", "dask", "matplotlib", "tqdm"]},
)
