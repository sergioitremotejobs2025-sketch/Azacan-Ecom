import graphene
from graphene_django.converter import convert_django_field
from pgvector.django import VectorField

class VectorFieldType(graphene.List):
    def __init__(self, description=None, required=False):
        super().__init__(graphene.Float, description=description, required=required)

@convert_django_field.register(VectorField)
def convert_vector_field(field, registry=None):
    return VectorFieldType(
        description=field.help_text, 
        required=not field.null
    )
