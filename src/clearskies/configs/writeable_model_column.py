from __future__ import annotations

from clearskies.configs import model_column


class WriteableModelColumn(model_column.ModelColumn):
    def get_allowed_columns(self, model_class, column_configs):
        return self.get_allowed_columns_by_attribute_name(model_class, column_configs, "is_writeable")

    def my_description(self):
        return "writeable column"
