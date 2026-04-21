from __future__ import annotations

from clearskies.configs import model_column


class ReadableModelColumn(model_column.ModelColumn):
    """Configuration descriptor that validates a value is a readable column name on a model class."""

    def get_allowed_columns(self, model_class, column_configs):
        return self.get_allowed_columns_by_attribute_name(model_class, column_configs, "is_readable")

    def my_description(self):
        return "readable column"
