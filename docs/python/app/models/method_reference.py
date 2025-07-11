from clearskies.model import ModelClassReference
from . import method


class MethodReference(ModelClassReference):
    def get_model_class(self):
        return method.Method
