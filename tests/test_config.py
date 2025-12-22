import pytest
from deq_tanks.config import FieldConfig

class TestFieldConfig:
    """Unit tests for the FieldConfig class validation logic"""

    def test_valid_initialization(self):
        """Test that valid configurations are accepted for all types"""
        # Standard type
        fc = FieldConfig("AGOL", "SF", "Alias", FieldConfig.text)
        assert fc.field_type == FieldConfig.text

        # Static type
        fc = FieldConfig("AGOL", None, "Alias", FieldConfig.static, static_value="fixed")
        assert fc.static_value == "fixed"

        # Composite type
        fc = FieldConfig("AGOL", None, "Alias", FieldConfig.composite, composite_format="{f1}")
        assert fc.composite_format == "{f1}"

        # Flatten with dot
        fc = FieldConfig("AGOL", "Parent.Child", "Alias", FieldConfig.text, flatten=True)
        assert fc.flatten is True

    def test_invalid_field_type_raises_error(self):
        """Test that an invalid field type raises ValueError"""
        with pytest.raises(ValueError, match="Invalid field type: invalid_type"):
            FieldConfig("AGOL", "SF", "Alias", "invalid_type")

    def test_static_type_requires_value(self):
        """Test that static type requires a static_value"""
        with pytest.raises(ValueError, match="Field type 'static' must have a 'static_value'"):
            FieldConfig("AGOL", None, "Alias", FieldConfig.static, static_value=None)

    def test_non_static_type_rejects_value(self):
        """Test that non-static types cannot have a static_value"""
        with pytest.raises(ValueError, match="Field type 'text' cannot have a 'static_value'"):
            FieldConfig("AGOL", "SF", "Alias", FieldConfig.text, static_value="value")

    def test_composite_type_requires_format(self):
        """Test that composite type requires a composite_format"""
        with pytest.raises(ValueError, match="Field type 'composite' must have a 'composite_format'"):
            FieldConfig("AGOL", None, "Alias", FieldConfig.composite, composite_format=None)

    def test_non_composite_type_rejects_format(self):
        """Test that non-composite types cannot have a composite_format"""
        with pytest.raises(ValueError, match="Field type 'integer' cannot have a 'composite_format'"):
            FieldConfig("AGOL", "SF", "Alias", FieldConfig.integer, composite_format="{f}")

    def test_flatten_requires_dot_in_sf_field(self):
        """Test that flatten=True requires a dot in the sf_field name"""
        with pytest.raises(ValueError, match="Field 'NoDotField' cannot be flattened without a dot"):
            FieldConfig("AGOL", "NoDotField", "Alias", FieldConfig.text, flatten=True)
