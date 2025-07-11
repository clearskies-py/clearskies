import pathlib
from typing import Any
from collections import OrderedDict

import clearskies
from .builder import Builder


class Module(Builder):
    def __init__(self, branch, modules, classes, doc_root, nav_order):
        super().__init__(branch, modules, classes, doc_root, nav_order)
        self.class_list = branch["classes"]
        self.args_to_additional_attributes_map = branch.get("args_to_additional_attributes_map", {})

    def build(self):
        title_snake_case = clearskies.functional.string.title_case_to_snake_case(self.title.replace(" ", "")).replace(
            "_", "-"
        )
        section_folder_path = self.doc_root / title_snake_case
        source_class = self.classes.find(f"import_path={self.source}")
        self.make_index_from_class_overview(title_snake_case, source_class, section_folder_path)

        default_args = self.default_args()

        nav_order = 0
        for class_name in self.class_list:
            nav_order += 1
            source_class = self.classes.find(f"import_path={class_name}")
            title = source_class.name
            filename = clearskies.functional.string.title_case_to_snake_case(source_class.name).replace("_", "-")
            class_doc = self.build_header(source_class.name, filename, title_snake_case, self.title, nav_order, False)
            (elevator_pitch, overview) = self.parse_overview_doc(
                self.raw_docblock_to_md(source_class.doc).lstrip("\n").lstrip(" ")
            )
            class_doc += f"\n\n# {title}\n\n{elevator_pitch}\n\n"
            main_doc = f"## Overview\n\n{overview}\n\n"
            table_of_contents = f" 1. [Overview](#overview)\n"

            # Find the documentation for all of our init args.
            arguments: dict[str, Any] = OrderedDict()
            for arg in source_class.init.all_args:
                if arg == "self":
                    continue
                arguments[arg] = {
                    "required": arg not in source_class.init.kwargs,
                    "doc": default_args.get(arg, ""),
                }

            # for various reasons, it's easier to extract docs for all the arguments at once:
            docs = self.extract_attribute_docs(source_class, list(arguments.keys()))
            for arg, doc in docs.items():
                # you would think that we would only get arguments that belong to our class, but this isn't the case
                # because the processing caches results from parent classes, and we don't always use all attributes
                # available from all our parents.
                if arg not in arguments:
                    continue
                arguments[arg]["doc"] = doc

            for index, arg in enumerate(arguments.keys()):
                arg_data = arguments[arg]
                table_of_contents += f" {index+2}. [{arg}](#{arg})\n"
                main_doc += f"## {arg}\n**" + ("Required" if arg_data["required"] else "Optional") + "**\n\n"
                main_doc += self.raw_docblock_to_md(arg_data["doc"].replace('"""', "")) + "\n\n"

            class_doc += f"{table_of_contents}\n{main_doc}"

            output_file = section_folder_path / f"{filename}.md"
            with output_file.open(mode="w") as doc_file:
                doc_file.write(class_doc)
