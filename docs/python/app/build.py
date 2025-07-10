import clearskies
from app import models
from app.prepare_doc_space import prepare_doc_space
from app.builders import Module

def build(modules: models.Module, classes: models.Class, config: str, project_root: str):
    doc_root = prepare_doc_space(project_root)
    nav_order_parent_count = {}

    for (index, branch) in enumerate(config["tree"]):
        nav_order_title_tracker = branch.get("parent", branch["title"])
        if nav_order_title_tracker not in nav_order_parent_count:
            nav_order_parent_count[nav_order_title_tracker] = 0
        nav_order_parent_count[nav_order_title_tracker] += 1
        builder_class = classes.find("import_path=" + branch["builder"]).type
        builder = builder_class(branch, modules, classes, doc_root, nav_order=nav_order_parent_count[nav_order_title_tracker] if branch.get("parent") else index+2)
        builder.build()
