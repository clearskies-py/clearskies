from clearskies.model import ModelClassReference
from . import module


class ModuleReference(ModelClassReference):
    def get_model_class(self):
        return module.Module
