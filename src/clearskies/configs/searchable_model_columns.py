from __future__ import annotations

from clearskies.configs import model_columns


class SearchableModelColumns(model_columns.ModelColumns):
    """Configuration descriptor that validates a list of searchable column names against a model class."""

    def get_allowed_columns(self, model_class, column_configs):
        return self.get_allowed_columns_by_attribute_name(model_class, column_configs, "is_searchable")

    def my_description(self):
        return "searchable column"
