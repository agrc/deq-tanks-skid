import logging

import palletjack

from deq_tanks import config

logger = logging.getLogger(config.SKID_NAME)


def convert_to_int(s):
    """Convert a string to an integer. If the string cannot be converted, return -1."""
    if s is None:
        return None

    try:
        return int(s)
    except ValueError:
        return -1


def flatten(x, child_field):
    if x is None:
        return None

    if not isinstance(x, dict):
        raise ValueError(f"Expected a dictionary, got {type(x)}")

    if child_field not in x:
        raise ValueError(
            f"Expected a child field '{child_field}', but not found in the dictionary"
        )

    return x[child_field]


class SalesForceRecords:
    """A helper class that extracts data from Salesforce for a specific table/api."""

    table = "table"
    feature_layer = "feature_layer"

    def __init__(
        self,
        salesforce_extractor: palletjack.extract.SalesforceRestLoader,
        salesforce_api: str,
        field_configs,
        where_clause,
    ):
        self.salesforce_extractor = salesforce_extractor
        self.salesforce_api = salesforce_api
        self.field_configs = field_configs
        self.where_clause = where_clause

    def extract_data_from_salesforce(self):
        """Load data from Salesforce into self.df dataframe

        Builds a string of needed column names for our specific needs and uses that in the REST query.
        """

        fields_string = self._build_columns_string()
        query = f"SELECT {fields_string} from {self.salesforce_api}"

        if self.where_clause is not None:
            query += f" WHERE {self.where_clause}"

        #: Main query with just our desired fields
        print(f"Querying Salesforce: {query}")
        self.df = self.salesforce_extractor.get_records(
            "services/data/v60.0/query/",
            query,
        )

        self.df.drop(columns=["attributes"], inplace=True)

        field_mappings = {
            c.sf_field: c.agol_field
            for c in self.field_configs
            if c.sf_field is not None
        }
        self.df.rename(mapper=field_mappings, axis=1, inplace=True)

        fields_to_drop = []
        for field_config in self.field_configs:
            if field_config.flatten:
                parts = field_config.sf_field.split(".")
                parent_field = parts[0]
                child_field = parts[1]
                self.df[field_config.agol_field] = self.df[parent_field].apply(
                    lambda x: flatten(x, child_field)
                )
                fields_to_drop.append(parent_field)
            if field_config.field_type == config.FieldConfig.static:
                self.df[field_config.agol_field] = field_config.static_value
            elif field_config.field_type == config.FieldConfig.integer:
                self.df[field_config.agol_field] = self.df[
                    field_config.agol_field
                ].apply(convert_to_int)
            elif field_config.field_type == config.FieldConfig.text:
                self.df[field_config.agol_field] = self.df[
                    field_config.agol_field
                ].apply(str)
            elif field_config.field_type == config.FieldConfig.composite:
                self.df[field_config.agol_field] = self.df.apply(
                    lambda x: field_config.composite_format.format(**dict(x)), axis=1
                )

        #: drop these fields after we've processed them since there may be more than one nested field in a single parent field
        if len(fields_to_drop) > 0:
            self.df.drop(columns=fields_to_drop, inplace=True)

        #: ints
        self.df = palletjack.transform.DataCleaning.switch_to_nullable_int(
            self.df,
            [
                c.agol_field
                for c in self.field_configs
                if c.field_type == config.FieldConfig.integer
            ],
        )

        #: floats
        self.df = palletjack.transform.DataCleaning.switch_to_float(
            self.df,
            [
                c.agol_field
                for c in self.field_configs
                if c.field_type == config.FieldConfig.float
            ],
        )

        #: dates
        self.df = palletjack.transform.DataCleaning.switch_to_datetime(
            self.df,
            [c.agol_field for c in self.field_configs if c.field_type == c.date],
        )

    def _build_columns_string(self) -> str:
        """Build a string of needed columns for the SOQL query based on field mapping and some custom fields

        Returns:
            str: A comma-delimited string of needed columns for the SOQL query
        """
        fields = list(
            [c.sf_field for c in self.field_configs if c.sf_field is not None]
        )
        fields_string = ",".join(fields)

        return fields_string
