import pytest

from deq_tanks.config import FieldConfig


class TestFieldConfig:
    """Unit tests for the FieldConfig class validation logic"""

    @pytest.mark.parametrize("field_type", [FieldConfig.text, FieldConfig.integer, FieldConfig.float, FieldConfig.date])
    def test_valid_initialization(self, field_type):
        """Test that valid configurations are accepted for all types"""
        # Standard types
        fc = FieldConfig("AGOL", "SF", "Alias", field_type)
        assert fc.field_type == field_type

    def test_valid_static_initialization(self):
        """Test that valid static configuration is accepted"""
        fc = FieldConfig("AGOL", None, "Alias", FieldConfig.static, static_value="fixed")
        assert fc.static_value == "fixed"
        assert fc.field_type == FieldConfig.static

    def test_valid_composite_initialization(self):
        """Test that valid composite configuration is accepted"""
        fc = FieldConfig("AGOL", None, "Alias", FieldConfig.composite, composite_format="{f1}")
        assert fc.composite_format == "{f1}"
        assert fc.field_type == FieldConfig.composite

    def test_valid_flatten_initialization(self):
        """Test that valid flatten configuration is accepted"""
        fc = FieldConfig("AGOL", "Parent.Child", "Alias", FieldConfig.text, flatten=True)
        assert fc.flatten is True

    def test_flatten_false_with_dot(self):
        """Test that flatten=False (default) works with a dot in the sf_field name"""
        fc = FieldConfig("AGOL", "Parent.Child", "Alias", FieldConfig.text)
        assert fc.flatten is False
        assert fc.sf_field == "Parent.Child"

    def test_flatten_true_with_multiple_dots(self):
        """Test that flatten=True works with multiple dots in the sf_field name"""
        fc = FieldConfig("AGOL", "Grandparent.Parent.Child", "Alias", FieldConfig.text, flatten=True)
        assert fc.flatten is True

    def test_invalid_field_type_raises_error(self):
        """Test that an invalid field type raises ValueError"""
        with pytest.raises(ValueError, match="Invalid field type: invalid_type"):
            FieldConfig("AGOL", "SF", "Alias", "invalid_type")

    def test_static_type_requires_value(self):
        """Test that static type requires a static_value"""
        with pytest.raises(ValueError, match="Field type 'static' must have a 'static_value'"):
            FieldConfig("AGOL", None, "Alias", FieldConfig.static, static_value=None)

    @pytest.mark.parametrize(
        "field_type",
        [FieldConfig.text, FieldConfig.integer, FieldConfig.float, FieldConfig.date, FieldConfig.composite],
    )
    def test_non_static_type_rejects_value(self, field_type):
        """Test that non-static types cannot have a static_value"""
        with pytest.raises(ValueError, match=f"Field type '{field_type}' cannot have a 'static_value'"):
            FieldConfig("AGOL", "SF", "Alias", field_type, static_value="value")

    def test_composite_type_requires_format(self):
        """Test that composite type requires a composite_format"""
        with pytest.raises(ValueError, match="Field type 'composite' must have a 'composite_format'"):
            FieldConfig("AGOL", None, "Alias", FieldConfig.composite, composite_format=None)

    @pytest.mark.parametrize(
        "field_type", [FieldConfig.text, FieldConfig.integer, FieldConfig.float, FieldConfig.date, FieldConfig.static]
    )
    def test_non_composite_type_rejects_format(self, field_type):
        """Test that non-composite types cannot have a composite_format"""
        kwargs = {"composite_format": "{f}"}
        if field_type == FieldConfig.static:
            kwargs["static_value"] = "value"

        with pytest.raises(ValueError, match=f"Field type '{field_type}' cannot have a 'composite_format'"):
            FieldConfig("AGOL", "SF", "Alias", field_type, **kwargs)

    def test_flatten_requires_dot_in_sf_field(self):
        """Test that flatten=True requires a dot in the sf_field name"""
        with pytest.raises(ValueError, match="Field 'NoDotField' cannot be flattened without a dot"):
            FieldConfig("AGOL", "NoDotField", "Alias", FieldConfig.text, flatten=True)
