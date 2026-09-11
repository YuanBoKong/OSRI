# System Functionality

## Data management

The backend provides interfaces for reading, editing, importing, exporting, and validating country-year input data and calculation outputs. Input files are organized by indicator and stored in JSON format.

## OSRI calculation

`system/calculate.py` implements the global country-year calculation pipeline. It calculates the open-access, open-data, and open-science-policy components, their intermediate indicators, normalized dimension outputs, and the composite score.

`system/calculate_aggregation.py` implements the aggregation calculation mode. The calculation modules save all intermediate and final outputs as JSON files.

## Data validation and storage

`system/data_validation.py` validates the structure of calculation inputs and outputs. `system/file_storage.py` provides atomic JSON writing, file locking, and revision support for data-management operations.

## Web interface

The Vue frontend in `system/frontend/` provides pages for input-data management, calculation-output review, and access to the visualization application.

The visualization application in `vis/` provides dynamic ranking charts, tiered readiness distributions, rank-change charts, line charts, continent summaries, and comparison charts.

## Deployment utilities

Docker, Docker Compose, Nginx, file-synchronization, and data-conversion utilities are included for local and server deployment.
