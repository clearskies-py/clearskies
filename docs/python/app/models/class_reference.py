from clearskies.model import ModelClassReference
from . import class_model


class ClassReference(ModelClassReference):
    def get_model_class(self):
        return class_model.Class
