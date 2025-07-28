import pathlib
from typing import Any
from collections import OrderedDict
import re

import clearskies
from .builder import Builder


class SingleClassToSection(Builder):
    def __init__(self, branch, modules, classes, doc_root, nav_order):
        super().__init__(branch, modules, classes, doc_root, nav_order)
        self.docs = branch["docs"]

    def build(self):
        section_name = clearskies.functional.string.title_case_to_snake_case(self.title).replace("_", "-")
        section_folder_path = self.doc_root / section_name
        source_class = self.classes.find(f"import_path={self.source}")
        self.make_index_from_class_overview(section_name, source_class, section_folder_path)

        for index, doc_data in enumerate(self.docs):
            title = doc_data["title"]
            title_snake_case = clearskies.functional.string.title_case_to_snake_case(title.replace(" ", "")).replace(
                "_", "-"
            )
            doc = self.build_header(title, title_snake_case, section_name, self.title, index + 1, False)
            doc += f"\n\n# {title}\n\n"
            table_of_contents = ""
            attribute_docs = ""

            for index, attribute_name in enumerate(doc_data["attributes"]):
                attribute = source_class.attributes.find(f"name={attribute_name}")
                table_of_contents += f" {index+1}. [{attribute_name}]({title_snake_case}.html#{attribute_name})\n"
                attribute_docs += f"\n\n## {attribute_name}\n\n"
                attribute_docs += re.sub("\n    ", "\n", self.raw_docblock_to_md(attribute.doc))

            doc += f"{table_of_contents}{attribute_docs}"

            output_file = section_folder_path / f"{title_snake_case}.md"
            with output_file.open(mode="w") as doc_file:
                doc_file.write(doc)
