from typing import Any, Callable, Type
from types import ModuleType
import sys
import importlib

import clearskies
import clearskies.model
import clearskies.column
import clearskies.query
from clearskies.autodoc.schema import Schema as AutoDocSchema


class ModuleBackend(clearskies.backends.Backend):
    _search_functions = {
        "id": lambda module, value: id(module) == int(value),
        "is_builtin": lambda module, value: (0 if hasattr(module, "__file__") else 1) == int(value),
        "source_file": lambda module, value: (module.__file__ if hasattr(module, "__file__") else "") == value,
        "module": lambda module, value: id(module) == id(value),
    }

    def update(self, id: int | str, data: dict[str, Any], model: clearskies.model.Model) -> dict[str, Any]:
        """
        Updates the record with the given id with the information from the data dictionary
        """
        raise Exception(f"The {self.__class__.__name__} only supports read operations: update is not allowed")

    def create(self, data: dict[str, Any], model: clearskies.model.Model) -> dict[str, Any]:
        """
        Creates a record with the information from the data dictionary
        """
        raise Exception(f"The {self.__class__.__name__} only supports read operations: create is not allowed")

    def delete(self, id: int | str, model: clearskies.model.Model) -> bool:
        """
        Deletes the record with the given id
        """
        raise Exception(f"The {self.__class__.__name__} only supports read operations: delete is not allowed")

    def count(self, query: clearskies.query.Query) -> int:
        """
        Returns the number of records which match the given query configuration
        """
        return len(records(query))

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
                raise ValueError(f"The ModuleBackend received {attribute_name} in a query but doesn't support this.")

        for condition in query.conditions:
            if condition.operator != "=":
                raise ValueError("The ModuleBackend only supports searching with the equals operator")

        module_name_condition = query.conditions_by_column.get("import_path", query.conditions_by_column.get("name"))
        if module_name_condition:
            module_name = module_name_condition[0].values[0]
            module = importlib.import_module(module_name)
            return [self.unpack(module)]

        matching_modules = []
        module_names = set(sys.modules) & set(globals())
        for module_name in module_names:
            if module_name not in sys.modules:
                continue

            module = sys.modules[module_name]
            matches = True
            for condition in query.conditions:
                if condition.column_name not in self._search_functions:
                    continue
                if not self._search_functions[condition.column_name](module, condition.values[0]):
                    matches = False

            if not matches:
                continue

            matching_modules.append(self.unpack(module))

        return self.paginate(matching_modules, query)

    def unpack(self, module: ModuleType) -> dict[str, Any]:
        return {
            "id": id(module),
            "import_path": module.__name__,
            "name": module.__name__,
            "is_builtin": not hasattr(module, "__file__"),
            "source_file": module.__file__ if hasattr(module, "__file__") else "",
            "doc": module.__doc__,
            "module": module,
        }

    def paginate(self, records, query):
        return records

    def validate_pagination_data(self, data: dict[str, Any], case_mapping: Callable) -> str:
        extra_keys = set(data.keys()) - set(self.allowed_pagination_keys())
        if len(extra_keys):
            key_name = case_mapping("start")
            return "Invalid pagination key(s): '" + "','".join(extra_keys) + f"'.  Only '{key_name}' is allowed"
        if "start" not in data:
            key_name = case_mapping("start")
            return f"You must specify '{key_name}' when setting pagination"
        start = data["start"]
        try:
            start = int(start)
        except:
            key_name = case_mapping("start")
            return f"Invalid pagination data: '{key_name}' must be a number"
        return ""

    def allowed_pagination_keys(self) -> list[str]:
        return ["start"]

    def documentation_pagination_next_page_response(self, case_mapping: Callable[[str], str]) -> list[Any]:
        return [AutoDocInteger(case_mapping("start"), example=0)]

    def documentation_pagination_next_page_example(self, case_mapping: Callable[[str], str]) -> dict[str, Any]:
        return {case_mapping("start"): 0}

    def documentation_pagination_parameters(
        self, case_mapping: Callable[[str], str]
    ) -> list[tuple[AutoDocSchema, str]]:
        return [
            (
                AutoDocInteger(case_mapping("start"), example=0),
                "The zero-indexed record number to start listing results from",
            )
        ]
