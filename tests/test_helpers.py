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

    def test_convert_invalid_string_returns_negative_one(self):
        """Test that invalid string returns -1"""
        assert helpers.convert_to_int("not a number") == -1

    def test_convert_empty_string_returns_negative_one(self):
        """Test that empty string returns -1"""
        assert helpers.convert_to_int("") == -1


class TestApplyFieldMappingsAndTransformations:
    """Integration tests for apply_field_mappings_and_transformations"""

    def test_basic_field_renaming(self):
        """Test that basic field mapping renames columns correctly"""
        df = pd.DataFrame({"sf_field1": ["a", "b"], "sf_field2": [1, 2]})
        field_configs = [
            config.FieldConfig(
                "agol_field1", "sf_field1", "Alias1", config.FieldConfig.text
            ),
            config.FieldConfig(
                "agol_field2", "sf_field2", "Alias2", config.FieldConfig.integer
            ),
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
            config.FieldConfig(
                "other_field", "OtherField", "Other", config.FieldConfig.text
            ),
        ]

        result = helpers.apply_field_mappings_and_transformations(df, field_configs)

        assert "nested_field" in result.columns
        assert "Parent" not in result.columns
        assert list(result["nested_field"]) == ["value1", "value2"]

    def test_static_field_addition(self):
        """Test that static fields are added with correct values"""
        df = pd.DataFrame({"sf_field": ["a", "b"]})
        field_configs = [
            config.FieldConfig(
                "agol_field", "sf_field", "Field", config.FieldConfig.text
            ),
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
            config.FieldConfig(
                "number", "num_field", "Number", config.FieldConfig.integer
            ),
        ]

        result = helpers.apply_field_mappings_and_transformations(df, field_configs)

        assert result["number"].dtype == "Int64"
        assert result["number"][0] == 123
        assert result["number"][1] == 456
        assert result["number"][2] == -1

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
            config.FieldConfig(
                "text_field", "mixed_field", "Text", config.FieldConfig.text
            ),
        ]

        result = helpers.apply_field_mappings_and_transformations(df, field_configs)

        assert result["text_field"][0] == "123"
        assert result["text_field"][1] == "text"
        assert result["text_field"][2] == "None"
