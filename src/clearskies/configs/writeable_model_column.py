from __future__ import annotations

from clearskies.configs import model_column


class WriteableModelColumn(model_column.ModelColumn):
    """Configuration descriptor that validates a value is a writeable column name on a model class."""

    def get_allowed_columns(self, model_class, column_configs):
        return self.get_allowed_columns_by_attribute_name(model_class, column_configs, "is_writeable")

    def my_description(self):
        return "writeable column"
