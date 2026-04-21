from __future__ import annotations

from clearskies.configs import model_columns


class WriteableModelColumns(model_columns.ModelColumns):
    """Configuration descriptor that validates a list of writeable column names against a model class."""

    def get_allowed_columns(self, model_class, column_configs):
        return self.get_allowed_columns_by_attribute_name(model_class, column_configs, "is_writeable")

    def my_description(self):
        return "writeable column"
