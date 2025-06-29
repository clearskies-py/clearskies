import inspect
from typing import Any, Self

import clearskies
from app import backends, columns

class Method(clearskies.Model):
    id_column_name = "id"
    backend = backends.AttributeBackend()

    id = clearskies.columns.Integer()
    name = clearskies.columns.String()
    type = columns.Class()
    doc = clearskies.columns.String()
    attribute = columns.Any()
    parent_class = columns.Class()

    args = columns.Any()
    kwargs = columns.Any()
    all_args = columns.Any()
    defaults = columns.Any()
