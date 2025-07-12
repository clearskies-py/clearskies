import re
import tokenize
import pathlib


class Builder:
    _attribute_cache: dict[str, str] = {}

    def __init__(self, branch, modules, classes, doc_root, nav_order):
        self.modules = modules
        self.classes = classes
        self.doc_root = pathlib.Path(doc_root)
        self.title = branch["title"]
        self.source = branch["source"]
        self.nav_order = nav_order
        self._attribute_cache = {}

    def make_index_from_class_overview(self, title_snake_case, source_class, section_folder_path):
        filename = "index"
        section_folder_path.mkdir(exist_ok=True)

        doc = self.build_header(self.title, filename, title_snake_case, None, self.nav_order, True)
        (elevator_pitch, overview) = self.parse_overview_doc(
            self.raw_docblock_to_md(source_class.doc).lstrip("\n").lstrip(" ")
        )
        doc += f"\n\n# {self.title}\n\n{elevator_pitch}\n\n## Overview\n\n{overview}"

        output_file = section_folder_path / f"{filename}.md"
        with output_file.open(mode="w") as doc_file:
            doc_file.write(doc)

    def parse_overview_doc(self, overview_doc):
        parts = overview_doc.lstrip("\n").split("\n", 1)
        if len(parts) < 2:
            return (parts[0], "")
        return (parts[0], parts[1].lstrip(" "))

    def extract_attribute_docs(self, source_class, argument_names, additional_attribute_sources=[]):
        """
        Fetch the docblocks for class arguments.

        Sadly, python doesn't support docblocks on class arguments.  I only discovered this after writing all
        the docblocs this way.  Still, I don't want to move my docblocs, because puttig them on arguments is
        legitimately the place where they make the most sense.  So, we have to use the python parsing capabilities
        built into python in order to extract them ourselves.  Very exciting... :cry:

        We substantially simplify this process (in a way that hopefully works) by setting stringent requirements
        for how our docblocks need to be defined.  The docblock must come before the argument and they must be
        at the top of the class.  In addition, when we are called, we are provided with a list of all argument
        names so that we are looking for a specific list of things rather than searching more generically for
        a series of documented arguments.  So, we're looking for a pattern of:

         1. tokenize.STRING
         2. tokenize.NEWLINE
         3. tokenize.NAME

        This will probably match a bunch of things, which is where our list of argument names comes in.
        Also, we'll only use the first combination of these things we find, which menas that attribute definitions
        must be at the top of the file. This will help us avoid getting confused by variable definitions with
        matching names later in the class.
        """
        # built in classes (which we will reach with our iterative approach) don't have a source file.
        if not source_class.source_file:
            return {}

        # we will iterate over base classes, and these often get re-used, so let's keep a cache
        if source_class.source_file in self._attribute_cache:
            return self._attribute_cache[source_class.source_file]

        doc_strings = {}
        with open(source_class.source_file, "r") as fp:
            # so this is both very simple and, hopefully, not prone to failure. The tokenization information that comes back from the
            # parser is surprisingly generic and vague.  However, we are looking for something
            last_string = ""
            for token_type, token_string, (srow, scol), (erow, ecol), line_content in tokenize.generate_tokens(
                fp.readline
            ):
                if token_type == tokenize.STRING:
                    last_string = token_string
                    continue
                if token_type == tokenize.NEWLINE:
                    continue
                if token_type != tokenize.NAME:
                    last_string = ""
                    continue
                if not last_string or token_string not in argument_names:
                    continue
                doc_strings[token_string] = last_string

        # and let's repeat this for any base classes just to make sure we don't miss anything.  Often attributes are defined in
        # bases and we want to use those docs if we don't have them.
        for base_class in source_class.base_classes:
            doc_strings = {
                **self.extract_attribute_docs(base_class, argument_names),
                **doc_strings,
            }

        for additional_source_class in additional_attribute_sources:
            doc_strings = {
                **self.extract_attribute_docs(additional_source_class, argument_names),
                **doc_strings,
            }

        self._attribute_cache[source_class.source_file] = doc_strings
        return doc_strings

    def build_header(self, title, filename, section_name, parent, nav_order, has_children):
        permalink = "/docs/" + (f"{section_name}/" if section_name else "") + f"{filename}.html"
        header = f"""---
layout: default
title: {title}
permalink: {permalink}
nav_order: {nav_order}
"""
        if parent:
            header += f"parent: {parent}\n"
        if has_children:
            header += "has_children: true\n"
        header += f"---"
        return header

    def raw_docblock_to_md(self, docblock):
        return re.sub(r"\n    ", "\n", docblock)

    def default_args(self):
        default_args = {}
        for key, value in self.args_to_additional_attributes_map.items():
            parts = value.split(".")
            import_path = ".".join(parts[:-1])
            attribute_name = parts[-1]
            source_class = self.classes.find(f"import_path={import_path}")
            doc = source_class.attributes.where(f"name={attribute_name}").first().doc
            if doc:
                default_args[key] = self.raw_docblock_to_md(doc)
        return default_args
