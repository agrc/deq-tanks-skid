import pandas as pd
import pytest

from deq_tanks import config, helpers


class TestFlatten:
    """Unit tests for the flatten function"""

    def test_flatten_returns_child_value(self):
        """Test that flatten successfully extracts a nested child field"""
        input_dict = {"Child": "value123", "Other": "other_value"}
        result = helpers.flatten(input_dict, "Child")
        assert result == "value123"

    def test_flatten_with_none_input(self):
        """Test that flatten returns None when input is None"""
        result = helpers.flatten(None, "Child")
        assert result is None

    def test_flatten_raises_error_on_non_dict(self):
        """Test that flatten raises ValueError when input is not a dictionary"""
        with pytest.raises(ValueError, match="Expected a dictionary"):
            helpers.flatten("not a dict", "Child")

    def test_flatten_raises_error_on_missing_child(self):
        """Test that flatten raises ValueError when child field is missing"""
        input_dict = {"OtherChild": "value", "Another": "data"}
        with pytest.raises(ValueError, match="Expected a child field 'Child'"):
            helpers.flatten(input_dict, "Child")

    def test_flatten_with_numeric_child_value(self):
        """Test that flatten works with numeric child values"""
        input_dict = {"Number": 42, "String": "text"}
        result = helpers.flatten(input_dict, "Number")
        assert result == 42

    def test_flatten_with_nested_dict_child_value(self):
        """Test that flatten can return nested dictionaries as values"""
        input_dict = {"Nested": {"Deep": "value"}, "Other": "data"}
        result = helpers.flatten(input_dict, "Nested")
        assert result == {"Deep": "value"}


class TestConvertToInt:
    """Unit tests for the convert_to_int function"""

    def test_convert_valid_string(self):
        """Test conversion of valid string to int"""
        assert helpers.convert_to_int("123") == 123

    def test_convert_none_returns_none(self):
        """Test that None input returns None"""
        assert helpers.convert_to_int(None) is None

    def test_convert_invalid_string_returns_none(self):
        """Test that invalid string returns None"""
        assert helpers.convert_to_int("not a number") is None

    def test_convert_empty_string_returns_none(self):
        """Test that empty string returns None"""
        assert helpers.convert_to_int("") is None


class TestApplyFieldMappingsAndTransformations:
    """Integration tests for apply_field_mappings_and_transformations"""

    def test_basic_field_renaming(self):
        """Test that basic field mapping renames columns correctly"""
        df = pd.DataFrame({"sf_field1": ["a", "b"], "sf_field2": [1, 2]})
        field_configs = [
            config.FieldConfig("agol_field1", "sf_field1", "Alias1", config.FieldConfig.text),
            config.FieldConfig("agol_field2", "sf_field2", "Alias2", config.FieldConfig.integer),
        ]

        result = helpers.apply_field_mappings_and_transformations(df, field_configs)

        assert "agol_field1" in result.columns
        assert "agol_field2" in result.columns
        assert "sf_field1" not in result.columns
        assert "sf_field2" not in result.columns

    def test_flatten_transformation(self):
        """Test that flatten transformation works on nested fields"""
        df = pd.DataFrame(
            {
                "Parent": [{"Child": "value1"}, {"Child": "value2"}],
                "OtherField": ["a", "b"],
            }
        )
        field_configs = [
            config.FieldConfig(
                "nested_field",
                "Parent.Child",
                "Nested Field",
                config.FieldConfig.text,
                flatten=True,
            ),
            config.FieldConfig("other_field", "OtherField", "Other", config.FieldConfig.text),
        ]

        result = helpers.apply_field_mappings_and_transformations(df, field_configs)

        assert "nested_field" in result.columns
        assert "Parent" not in result.columns
        assert list(result["nested_field"]) == ["value1", "value2"]

    def test_static_field_addition(self):
        """Test that static fields are added with correct values"""
        df = pd.DataFrame({"sf_field": ["a", "b"]})
        field_configs = [
            config.FieldConfig("agol_field", "sf_field", "Field", config.FieldConfig.text),
            config.FieldConfig(
                "static_field",
                None,
                "Static",
                config.FieldConfig.static,
                static_value="constant",
            ),
        ]

        result = helpers.apply_field_mappings_and_transformations(df, field_configs)

        assert "static_field" in result.columns
        assert all(result["static_field"] == "constant")

    def test_integer_conversion(self):
        """Test that integer fields are properly converted"""
        df = pd.DataFrame({"num_field": ["123", "456", "invalid"]})
        field_configs = [
            config.FieldConfig("number", "num_field", "Number", config.FieldConfig.integer),
        ]

        result = helpers.apply_field_mappings_and_transformations(df, field_configs)

        assert result["number"].dtype == "Int64"
        assert result["number"][0] == 123
        assert result["number"][1] == 456
        assert result["number"][2] is pd.NA

    def test_composite_field_creation(self):
        """Test that composite fields combine multiple fields"""
        df = pd.DataFrame({"first": ["John", "Jane"], "last": ["Doe", "Smith"]})
        field_configs = [
            config.FieldConfig("first", "first", "First", config.FieldConfig.text),
            config.FieldConfig("last", "last", "Last", config.FieldConfig.text),
            config.FieldConfig(
                "full_name",
                None,
                "Full Name",
                config.FieldConfig.composite,
                composite_format="{first} {last}",
            ),
        ]

        result = helpers.apply_field_mappings_and_transformations(df, field_configs)

        assert "full_name" in result.columns
        assert list(result["full_name"]) == ["John Doe", "Jane Smith"]

    def test_column_ordering_matches_field_configs(self):
        """Test that output columns are ordered according to field_configs"""
        df = pd.DataFrame({"field_z": [1], "field_a": [2], "field_m": [3]})
        field_configs = [
            config.FieldConfig("a", "field_a", "A", config.FieldConfig.integer),
            config.FieldConfig("m", "field_m", "M", config.FieldConfig.integer),
            config.FieldConfig("z", "field_z", "Z", config.FieldConfig.integer),
        ]

        result = helpers.apply_field_mappings_and_transformations(df, field_configs)

        assert list(result.columns) == ["a", "m", "z"]

    def test_text_conversion(self):
        """Test that text fields are converted to strings"""
        df = pd.DataFrame({"mixed_field": [123, "text", None]})
        field_configs = [
            config.FieldConfig("text_field", "mixed_field", "Text", config.FieldConfig.text),
        ]

        result = helpers.apply_field_mappings_and_transformations(df, field_configs)

        assert result["text_field"][0] == "123"
        assert result["text_field"][1] == "text"
        assert result["text_field"][2] == "None"


class TestSalesForceRecords:
    """Unit tests for the SalesForceRecords class"""

    def test_build_columns_string_joins_fields(self):
        """Test that _build_columns_string correctly joins sf_field names and ignores None values"""
        field_configs = [
            config.FieldConfig("agol1", "sf_field1", "Alias1", config.FieldConfig.text),
            config.FieldConfig("agol2", "sf_field2", "Alias2", config.FieldConfig.text),
            config.FieldConfig("static", None, "Static", config.FieldConfig.static, static_value="val"),
        ]
        sf_records = helpers.SalesForceRecords(None, "Table__c", field_configs, None)

        result = sf_records._build_columns_string()

        assert result == "sf_field1,sf_field2"

    def test_extract_data_from_salesforce_calls_loader_and_processes(self, mocker):
        """Test that extract_data_from_salesforce queries Salesforce and cleans the result"""
        mock_loader = mocker.Mock()
        # Mock the dataframe returned by Salesforce
        input_df = pd.DataFrame({"sf_field1": ["value1"], "attributes": [{"type": "Table__c"}]})
        mock_loader.get_records.return_value = input_df

        field_configs = [
            config.FieldConfig("agol_field1", "sf_field1", "Alias1", config.FieldConfig.text),
        ]

        # Mock apply_field_mappings_and_transformations to isolate the test
        mock_apply = mocker.patch("deq_tanks.helpers.apply_field_mappings_and_transformations")
        processed_df = pd.DataFrame({"agol_field1": ["value1"]})
        mock_apply.return_value = processed_df

        sf_records = helpers.SalesForceRecords(mock_loader, "Table__c", field_configs, "Field='Value'")
        sf_records.extract_data_from_salesforce()

        # Verify query construction
        expected_query = "SELECT sf_field1 from Table__c WHERE Field='Value'"
        mock_loader.get_records.assert_called_once_with("services/data/v60.0/query/", expected_query)

        # Verify attributes column was dropped and transformation was applied
        assert "attributes" not in sf_records.df.columns
        assert sf_records.df.equals(processed_df)
        mock_apply.assert_called_once()

    def test_extract_data_from_salesforce_no_where_clause(self, mocker):
        """Test query construction when no where clause is provided"""
        mock_loader = mocker.Mock()
        mock_loader.get_records.return_value = pd.DataFrame({"sf": [1], "attributes": [2]})
        mocker.patch("deq_tanks.helpers.apply_field_mappings_and_transformations", side_effect=lambda df, configs: df)

        field_configs = [config.FieldConfig("agol", "sf", "Alias", config.FieldConfig.text)]
        sf_records = helpers.SalesForceRecords(mock_loader, "Table__c", field_configs, None)

        sf_records.extract_data_from_salesforce()

        expected_query = "SELECT sf from Table__c"
        mock_loader.get_records.assert_called_once_with("services/data/v60.0/query/", expected_query)
