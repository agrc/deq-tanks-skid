# DEQ Tanks Skid - AI Coding Instructions

This project is a Python ETL "skid" that synchronizes data from DEQ Tanks Salesforce to ArcGIS Online (AGOL) hosted feature layers. It is designed to run as a Google Cloud Function but supports local development.

## Architecture & Key Components

- **Entry Point**: `src/deq_tanks/main.py` (`process` function).
- **Core Logic**: The `Skid` class manages the workflow.
  - `update()`: Routine sync (Salesforce -> AGOL). Uses `palletjack` for ETL.
  - `publish()`: One-time setup to create/publish layers. **Requires `arcpy`**.
- **Data Extraction**: `src/deq_tanks/helpers.py` (`SalesForceRecords`) handles Salesforce queries and field mapping.
  - **Note**: The `facilities` dataset is extracted via a custom Apex endpoint (`services/apexrest/facilities`) directly in `main.py`.
- **Configuration**: `src/deq_tanks/config.py` defines field mappings (`FieldConfig`), API endpoints, and environment settings.
- **Dependencies**:
  - `ugrc-palletjack`: Custom library for ETL operations (extract, load, transform).
  - `agrc-supervisor`: Handles email notifications (SendGrid).
  - `arcgis`: Python API for ArcGIS.

## Development Workflow

- **Environment**: Python 3.13 (Conda recommended).
- **Install**: `pip install -e .[tests]` to install in editable mode with test dependencies.
- **Secrets**:
  - **Critical**: `src/deq_tanks/secrets/secrets.json` is required for local runs.
  - Copy `src/deq_tanks/secrets/secrets_template.json` to `secrets.json` and populate.
  - In Cloud Functions, secrets are mounted at `/secrets/app/secrets.json`.
- **Testing**: Run `pytest` (configured in `pyproject.toml` with `ruff` and coverage).

## Common Tasks

### Adding/Modifying Fields

1.  Update `src/deq_tanks/config.py`.
2.  Add a `FieldConfig` object to the relevant list (e.g., `RELEASES_FIELDS`).
    ```python
    FieldConfig(
        agol_field="new_field",
        sf_field="Salesforce_Field__c",
        alias="New Field Alias",
        field_type=FieldConfig.text  # Also supports integer, float, date, static, composite
    )
    ```
3.  If `sf_field` is nested (e.g., `Parent.Child`), set `flatten=True` (handled in `helpers.py`).

### Running the Skid

- **Command**: `deq-tanks-skid` (installed via `setup.py` entry_points).
- **Mode Selection**: In `main.py`, the `process()` function calls `skid.publish()` or `skid.update()`.
  - Default is often `update()` for routine runs.
  - **Note**: `publish()` requires `arcpy` (Windows/ArcGIS Pro environment).

## Project Conventions

- **Logging**: Uses `logging` with a specific format. `Skid` initializes a file handler and stream handler.
- **Error Handling**: `supervisor` is used for notifications. Note that it is initialized with `handle_errors=False`, so it does not automatically catch unhandled exceptions.
- **Data Filtering**: The `facilities` dataset is filtered by UTM coordinates (Northing: 4,000,000-4,800,000; Easting: 150,000-750,000) to remove invalid records.
- **Dataframes**: Uses `pandas` and `arcgis.features.GeoAccessor` (Spatial DataFrame).
- **Linting**: Follows `ruff` configuration in `pyproject.toml`.

## Integration Details

- **Salesforce**: Uses REST API via `palletjack.extract.SalesforceRestLoader`.
- **AGOL**: Updates Feature Layers via `palletjack.load.ServiceUpdater`.
- **GCP**: Detects environment via metadata server check in `config.py`.
