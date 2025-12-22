#!/usr/bin/env python
# * coding: utf8 *
"""
Run the deq_tanks script as a cloud function.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from shutil import make_archive
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import arcgis
import pandas as pd
from arcgis.features import GeoAccessor
from arcgis.gis._impl._content_manager import SharingLevel
from palletjack import extract, load
from supervisor.message_handlers import SendGridHandler
from supervisor.models import MessageDetails, Supervisor

from deq_tanks import config, helpers, version


class Skid:
    def __init__(self):
        self.secrets = SimpleNamespace(**self._get_secrets())
        self.tempdir = TemporaryDirectory(ignore_cleanup_errors=True)
        self.tempdir_path = Path(self.tempdir.name)
        self.log_name = f"{config.LOG_FILE_NAME}.txt"
        self.log_path = self.tempdir_path / self.log_name
        self._initialize_supervisor()
        self.skid_logger = logging.getLogger(config.SKID_NAME)

        self.skid_logger.info("Initializing AGOL connection...")
        self.gis = arcgis.GIS(
            self.secrets.AGOL_ORG,
            self.secrets.AGOL_USER,
            self.secrets.AGOL_PASSWORD,
        )

        self.skid_logger.info("Initializing Salesforce connection...")
        if self.secrets.IS_DEV:
            salesforce_credentials = extract.SalesforceSandboxCredentials(
                self.secrets.SF_USERNAME,
                self.secrets.SF_PASSWORD,
                "",
                self.secrets.SF_CLIENT_SECRET,
                self.secrets.SF_CLIENT_ID,
            )
        else:
            salesforce_credentials = extract.SalesforceApiUserCredentials(
                self.secrets.SF_CLIENT_SECRET,
                self.secrets.SF_CLIENT_ID,
            )
        self.salesforce_extractor = extract.SalesforceRestLoader(
            self.secrets.SF_ORG,
            salesforce_credentials,
            sandbox=self.secrets.IS_DEV,
        )

    def __del__(self):
        self.tempdir.cleanup()

    @staticmethod
    def _get_secrets():
        """A helper method for loading secrets from either a GCF mount point or the local src/deq_tanks/secrets/secrets.json file

        Raises:
            FileNotFoundError: If the secrets file can't be found.

        Returns:
            dict: The secrets .json loaded as a dictionary
        """

        secret_folder = Path("/secrets")

        #: Try to get the secrets from the Cloud Function mount point
        if secret_folder.exists():
            return json.loads(Path("/secrets/app/secrets.json").read_text(encoding="utf-8"))

        #: Otherwise, try to load a local copy for local development
        #: This file path might not work if extracted to its own module
        secret_folder = Path(__file__).parent / "secrets"
        if secret_folder.exists():
            return json.loads((secret_folder / "secrets.json").read_text(encoding="utf-8"))

        raise FileNotFoundError("Secrets folder not found; secrets not loaded.")

    def _initialize_supervisor(self):
        """A helper method to set up logging and supervisor

        Returns:
            Supervisor: The supervisor object used for sending messages
        """

        skid_logger = logging.getLogger(config.SKID_NAME)
        skid_logger.setLevel(config.LOG_LEVEL)
        palletjack_logger = logging.getLogger("palletjack")
        palletjack_logger.setLevel(config.LOG_LEVEL)

        cli_handler = logging.StreamHandler(sys.stdout)
        cli_handler.setLevel(config.LOG_LEVEL)
        formatter = logging.Formatter(
            fmt="%(levelname)-7s %(asctime)s %(name)15s:%(lineno)5s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        cli_handler.setFormatter(formatter)

        log_handler = logging.FileHandler(self.log_path, mode="w")
        log_handler.setLevel(config.LOG_LEVEL)
        log_handler.setFormatter(formatter)

        skid_logger.addHandler(cli_handler)
        skid_logger.addHandler(log_handler)
        palletjack_logger.addHandler(cli_handler)
        palletjack_logger.addHandler(log_handler)

        #: Log any warnings at logging.WARNING
        #: Put after everything else to prevent creating a duplicate, default formatter
        #: (all log messages were duplicated if put at beginning)
        logging.captureWarnings(True)

        skid_logger.debug("Creating Supervisor object")
        self.supervisor = Supervisor(handle_errors=False)
        sendgrid_settings = config.SENDGRID_SETTINGS
        sendgrid_settings["api_key"] = self.secrets.SENDGRID_API_KEY
        self.supervisor.add_message_handler(
            SendGridHandler(
                sendgrid_settings=sendgrid_settings, client_name=config.SKID_NAME, client_version=version.__version__
            )
        )

    def _remove_log_file_handlers(self):
        """A helper function to remove the file handlers so the tempdir will close correctly"""

        loggers = [logging.getLogger(config.SKID_NAME), logging.getLogger("palletjack")]

        for logger in loggers:
            for handler in logger.handlers:
                try:
                    if self.log_name in handler.stream.name:
                        logger.removeHandler(handler)
                        handler.close()
                except Exception:
                    pass

    def _get_facilities(self) -> GeoAccessor:
        self.skid_logger.info("loading tank facility records from Salesforce...")

        dataframe = self.salesforce_extractor.get_records(
            "services/apexrest/facilities",
            "",
        )
        dataframe = helpers.apply_field_mappings_and_transformations(
            dataframe,
            config.FACILITIES_FIELDS,
        )

        #: filter out records with invalid coordinates
        dataframe = dataframe.query("NORTHING > 4000000 & NORTHING < 4800000 & EASTING > 150000 & EASTING < 750000")

        self.skid_logger.info("converting to spatial dataframe...")
        sdf = GeoAccessor.from_xy(dataframe, "EASTING", "NORTHING", sr=26912)

        self.skid_logger.info("projecting...")
        web_mercator = arcgis.geometry.SpatialReference(3857)
        sdf.spatial.project(web_mercator, "NAD_1983_To_WGS_1984_5")
        sdf.spatial.sr = web_mercator

        sdf = sdf.query("NORTHING > 0 & EASTING > 0")

        return sdf

    def _get_releases(self) -> pd.DataFrame:
        releases = helpers.SalesForceRecords(
            self.salesforce_extractor,
            config.RELEASES_API,
            config.RELEASES_FIELDS,
            where_clause=config.RELEASES_QUERY,
        )
        releases.extract_data_from_salesforce()

        return releases.df

    def _get_tanks(self) -> pd.DataFrame:
        tanks = helpers.SalesForceRecords(
            self.salesforce_extractor,
            config.TANKS_API,
            config.TANKS_FIELDS,
            where_clause=config.TANKS_QUERY,
        )
        tanks.extract_data_from_salesforce()

        return tanks.df

    def _get_compartments(self) -> pd.DataFrame:
        compartment = helpers.SalesForceRecords(
            self.salesforce_extractor,
            config.COMPARTMENTS_API,
            config.COMPARTMENTS_FIELDS,
            where_clause=config.COMPARTMENTS_QUERY,
        )
        compartment.extract_data_from_salesforce()

        return compartment.df

    def _publish_dataset(self, table_name, title, fields, sdf, type):
        """A private method intended to be run, on a machine with access to arcpy, prior to this skid being scheduled in the cloud that creates the assets that the skid will write to."""
        import arcpy  # pyright: ignore[reportMissingImports]

        #: save to a feature class just so that we can add field aliases
        self.skid_logger.info("saving to feature class...")
        fgdb_path = self.tempdir_path / f"{table_name}.gdb"
        feature_class_path = fgdb_path / table_name
        if arcpy.Exists(feature_class_path):
            self.skid_logger.info("deleting existing feature class...")
            arcpy.management.Delete(feature_class_path)
        elif not arcpy.Exists(fgdb_path):
            self.skid_logger.info("creating gdb...")
            arcpy.management.CreateFileGDB(
                str(fgdb_path.parent),
                fgdb_path.name,
            )

        if type == "layer":
            self.skid_logger.info("exporting to feature class...")
            sdf.spatial.to_featureclass(
                location=feature_class_path,
                sanitize_columns=False,
            )
        else:
            self.skid_logger.info("exporting to table...")
            sdf.spatial.to_table(
                location=feature_class_path,
                sanitize_columns=False,
            )

        self.skid_logger.info("adding field aliases...")
        aliases = {field.agol_field: field.alias for field in fields}
        for field in arcpy.Describe(str(feature_class_path)).fields:
            if field.name in aliases:
                arcpy.management.AlterField(
                    str(feature_class_path),
                    field.name,
                    new_field_alias=aliases[field.name],
                )

        #: this removes any locks on the FGDB that cause the zip to fail
        self.skid_logger.info("clearing workspace cache...")
        arcpy.management.ClearWorkspaceCache(str(fgdb_path))

        self.skid_logger.info("zipping and publishing...")
        zip_path = make_archive(
            str(fgdb_path.with_suffix("")),
            "zip",
            root_dir=fgdb_path.parent,
            base_dir=fgdb_path.name,
        )

        fgdb_item = self.gis.content.add(
            {
                "type": "File Geodatabase",
            },
            data=str(zip_path),
            folder="Interactive Map",
        )

        layer_item = fgdb_item.publish(
            publish_parameters={
                # "name": table_name if self.secrets.IS_DEV is False else f"{table_name}_dev",
                "name": table_name,
                "layerInfo": {
                    "capabilities": "Query",
                },
            },
        )

        manager = arcgis.features.FeatureLayerCollection.fromitem(layer_item).manager
        manager.update_definition({"capabilities": "Query,Extract"})
        # if self.secrets.IS_DEV:
        #     title += " (test)"
        #     layer_item.update({"tags": "test"})
        # else:
        layer_item.sharing.sharing_level = SharingLevel.EVERYONE
        layer_item.update({"title": title})

        print("cleaning up fgdb item...")
        fgdb_item.delete(permanent=True)

        print(f"feature layer published: {title} | {layer_item.id}")

    def update(self):
        start = datetime.now()

        self.skid_logger.info("Updating facilities...")
        facilities_sdf = self._get_facilities()
        facilities_loader = load.ServiceUpdater(
            self.gis,
            self.secrets.FACILITIES_ITEM_ID,
            working_dir=self.tempdir_path,
        )
        facilities_count = facilities_loader.truncate_and_load(facilities_sdf)

        self.skid_logger.info("Updating releases...")
        releases_df = self._get_releases()
        releases_loader = load.ServiceUpdater(
            self.gis,
            self.secrets.RELEASES_ITEM_ID,
            "table",
            working_dir=self.tempdir_path,
        )
        releases_count = releases_loader.truncate_and_load(releases_df)

        self.skid_logger.info("Updating tanks...")
        tanks_df = self._get_tanks()
        tanks_loader = load.ServiceUpdater(
            self.gis,
            self.secrets.TANKS_ITEM_ID,
            "table",
            working_dir=self.tempdir_path,
        )
        tanks_count = tanks_loader.truncate_and_load(tanks_df)

        self.skid_logger.info("Updating compartments...")
        compartments_df = self._get_compartments()
        compartments_loader = load.ServiceUpdater(
            self.gis,
            self.secrets.COMPARTMENTS_ITEM_ID,
            "table",
            working_dir=self.tempdir_path,
        )
        compartments_count = compartments_loader.truncate_and_load(compartments_df)

        end = datetime.now()

        summary_message = MessageDetails()
        summary_message.subject = f"{config.SKID_NAME} Update Summary"
        summary_rows = [
            f"{config.SKID_NAME} update {start.strftime('%Y-%m-%d')}",
            "=" * 20,
            "",
            f"Start time: {start.strftime('%H:%M:%S')}",
            f"End time: {end.strftime('%H:%M:%S')}",
            f"Duration: {str(end - start)}",
            "",
            f"{config.FACILITIES_TITLE} rows loaded: {facilities_count}",
            f"{config.RELEASES_TITLE} rows loaded: {releases_count}",
            f"{config.TANKS_TITLE} rows loaded: {tanks_count}",
            f"{config.COMPARTMENTS_TITLE} rows loaded: {compartments_count}",
        ]

        summary_message.message = "\n".join(summary_rows)
        summary_message.attachments = self.tempdir_path / self.log_name

        if config.IS_LOCAL_DEV:
            print(summary_message.message)
        else:
            self.supervisor.notify(summary_message)

        self._remove_log_file_handlers()

    def publish(self):
        """Publish new AGOL hosted feature layers"""

        #: NOTE: this method requires arcpy

        self.skid_logger.info("Publishing facilities...")
        facilities_sdf = self._get_facilities()
        self._publish_dataset(
            config.FACILITIES_TABLE_NAME,
            config.FACILITIES_TITLE,
            config.FACILITIES_FIELDS,
            facilities_sdf,
            "layer",
        )

        self.skid_logger.info("Publishing releases...")
        releases_df = self._get_releases()
        self._publish_dataset(
            config.RELEASES_TABLE_NAME,
            config.RELEASES_TITLE,
            config.RELEASES_FIELDS,
            releases_df,
            "table",
        )

        self.skid_logger.info("Publishing tanks...")
        tanks_df = self._get_tanks()
        self._publish_dataset(
            config.TANKS_TABLE_NAME,
            config.TANKS_TITLE,
            config.TANKS_FIELDS,
            tanks_df,
            "table",
        )

        self.skid_logger.info("Publishing compartments...")
        compartments_df = self._get_compartments()
        self._publish_dataset(
            config.COMPARTMENTS_TABLE_NAME,
            config.COMPARTMENTS_TITLE,
            config.COMPARTMENTS_FIELDS,
            compartments_df,
            "table",
        )

        self._remove_log_file_handlers()


def process() -> None:
    """Entry point triggered by the scheduler job

    Returns:
        None. The output is written to Cloud Logging.
    """

    skid = Skid()

    #: choose one of the following
    # skid.publish()  #: requires arcpy
    skid.update()


if __name__ == "__main__":
    process()
