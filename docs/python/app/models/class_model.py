import inspect
from typing import Any, Self

import clearskies
from app import models, backends, columns
from .attribute_reference import AttributeReference
from .method_reference import MethodReference


class Class(clearskies.Model):
    id_column_name = "id"
    backend = backends.ClassBackend()

    id = clearskies.columns.Integer()
    type = columns.Any()
    source_file = clearskies.columns.String()
    import_path = clearskies.columns.String()
    name = clearskies.columns.String(is_searchable=False)
    doc = clearskies.columns.String(is_searchable=False)
    module = columns.Module()
    base_classes = columns.BaseClasses()
    attributes = columns.Attributes(AttributeReference)
    methods = columns.Attributes(AttributeReference, filter=lambda attribute: callable(attribute.attribute))
    init = columns.Attribute(
        MethodReference,
        filter=lambda attribute: attribute.name == "__init__",
    )
