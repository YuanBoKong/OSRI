# Data Setup

The full OSRI dataset is distributed separately through Figshare.

## Global calculation data

Copy the contents of the following Figshare data-package directories into this repository:

- `reproduction_inputs/jsondata/` to `system/jsondata/`
- `reproduction_inputs/HDI.json` to `system/HDI.json`

The global calculation module reads these files directly and writes its results to `system/output/`.

## Aggregation mode

The repository also retains the aggregation calculation mode. It uses `system/jsondata_aggregation/` and writes results to `system/output_aggregation/`. Supply the corresponding aggregation input files in that directory when this optional mode is used.

## Data directories

The following runtime directories are excluded from version control. The visualization directories retain only the small static country and continent lookup files required by the web application.

- `system/jsondata/`
- `system/output/`
- `system/jsondata_aggregation/`
- `system/output_aggregation/`
- `vis/data/`
- `vis/data_aggregation/`

The backend synchronizes selected global and aggregation results to the visualization data directories after a calculation is completed.
