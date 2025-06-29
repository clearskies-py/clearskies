import inspect
from typing import Any, Self

import clearskies
from app import backends, columns
from . import class_reference

class Module(clearskies.Model):
    id_column_name = "id"
    backend = backends.ModuleBackend()

    id = clearskies.columns.Integer()
    import_path = clearskies.columns.String()
    source_file = clearskies.columns.String()
    is_builtin = clearskies.columns.Boolean()
    name = clearskies.columns.String()
    doc = clearskies.columns.String(is_searchable=False)
    module = columns.Module()
    classes = columns.ModuleClasses(class_reference.ClassReference)
