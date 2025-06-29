from typing import Any, Callable, Type
from types import ModuleType
import sys
import importlib
import inspect

import clearskies
import clearskies.model
import clearskies.column
import clearskies.query
from clearskies.autodoc.schema import Schema as AutoDocSchema
from app.backends.module_backend import ModuleBackend

class ClassBackend(ModuleBackend):
    _search_functions = {
        "id": lambda module, value: id(module) == int(value),
        "source_file": lambda module, value: (module.__file__ if hasattr(module, "__file__") else "") == value,
    }

    def records(
        self, query: clearskies.query.Query, next_page_data: dict[str, str | int] | None = None
    ) -> list[dict[str, Any]]:
        """
        Returns a list of records that match the given query configuration

        next_page_data is used to return data to the caller.  Pass in an empty dictionary, and it will be populated
        with the data needed to return the next page of results.  If it is still an empty dictionary when returned,
        then there is no additional data.
        """
        disallowed = ["joins", "selects", "group_by"]
        for attribute_name in disallowed:
            if getattr(query, attribute_name):
                raise ValueError(f"The ClassBackend received {attribute_name} in a query but doesn't support this.")

        for condition in query.conditions:
            if condition.operator != "=":
                raise ValueError("The ClassBackend only supports searching with the equals operator")

        if "import_path" in query.conditions_by_column:
            import_path = query.conditions_by_column["import_path"][0].values[0]
            path_parts = import_path.split(".")
            if len(path_parts) < 2:
                raise ValueError("In order to search for classes by import path you must provide the module and class name, e.g. `classes.find(\"import_path=clearskies.Endpoint\")`")
            class_name = path_parts[-1]
            module_path = ".".join(path_parts[0:-1])
            module = importlib.import_module(module_path)
            if not hasattr(module, class_name):
                raise ValueError(f"Module {import_path} has no class named {class_name}")
            Class = getattr(module, class_name)
            if not inspect.isclass(Class):
                raise ValueError(f"I was asked to import the class named '{import_path}' but this doesn't actually reference a class")
            return [self.unpack(Class, module)]

        if "module" not in query.conditions_by_column:
            raise ValueError("When searching for classes you must include a condition on either 'module' or 'import_path'")

        parent_module = query.conditions_by_column["module"][0].values[0]
        matching_classes = []
        for name in dir(parent_module):
            attribute = getattr(parent_module, name)
            if not inspect.isclass(attribute):
                continue

            matches = True
            for condition in query.conditions:
                if condition.column_name not in self._search_functions:
                    continue
                if not self._search_functions[condition.column_name](attribute, condition.values[0]):
                    matches = False

            if not matches:
                continue
            matching_classes.append(self.unpack(attribute, parent_module))

        return self.paginate(matching_classes, query)

    def unpack(self, Class: type, module: ModuleType) -> dict[str, Any]:
        source_file = ""
        try:
            # this fails for built ins
            source_file = inspect.getfile(Class)
        except TypeError:
            pass

        return {
            "id": id(Class),
            "import_path": Class.__module__ + "." + Class.__name__,
            "name": Class.__name__,
            "source_file": source_file,
            "doc": Class.__doc__,
            "module": module,
            "type": Class,
        }
