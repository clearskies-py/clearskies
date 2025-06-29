import clearskies
from app import models
from app.prepare_doc_space import prepare_doc_space
from app.builders import Module

def build(modules: models.Module, classes: models.Class, config: str, project_root: str):
    doc_root = prepare_doc_space(project_root)

    for (index, branch) in enumerate(config["tree"]):
        builder_class = classes.find("import_path=" + branch["builder"]).type
        builder = builder_class(branch, modules, classes, doc_root, nav_order=index+2)
        builder.build()
