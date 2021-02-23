# Census data for Demosearch

## Building the package

Because the package can spend a long time downloading census data, a Jupyter notebook 
will time out. So, to build this package: 

1. Run `invoke build` to build CSV files in the data directory. Use `--force` to overwrite existing files.
2. Run `mp build` to build the package

