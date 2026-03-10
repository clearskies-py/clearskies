from __future__ import annotations

from clearskies.configs import model_columns


class WriteableModelColumns(model_columns.ModelColumns):
    def get_allowed_columns(self, model_class, column_configs):
        result = []
        for name, column in column_configs.items():
            try:
                if column.is_writeable:
                    result.append(name)
            except KeyError:
                # Column not yet finalized during re-entrant get_columns() call.
                # Default to including it (is_writeable defaults to True).
                result.append(name)
        return result

    def my_description(self):
        return "writeable column"
