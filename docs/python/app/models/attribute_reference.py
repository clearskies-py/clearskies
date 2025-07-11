from clearskies.model import ModelClassReference
from . import attribute


class AttributeReference(ModelClassReference):
    def get_model_class(self):
        return attribute.Attribute
