from marshmallow import (
    Schema,
    fields,
    validate,
    validates_schema,
    ValidationError,
)


TIPOS_COMIDA = (
    "desayuno",
    "almuerzo",
    "merienda",
    "cena",
)


class EntregaPersonaSchema(Schema):
    """Persona incluida en una entrega."""

    person_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
    )

    tipo_menu_entregado_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
    )


class EntregaCrearSchema(Schema):
    """Contrato de entrada para registrar una entrega."""

    responsable_retiro = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200),
    )

    tipo_comida = fields.String(
        required=True,
        validate=validate.OneOf(TIPOS_COMIDA),
    )

    personas = fields.List(
        fields.Nested(EntregaPersonaSchema),
        required=True,
        validate=validate.Length(min=1),
    )


class EntregaFiltrosSchema(Schema):
    """Filtros para listar entregas."""

    fecha = fields.Date(
        required=False,
        allow_none=True,
    )

    sector_id = fields.Integer(
        required=False,
        allow_none=True,
        validate=validate.Range(min=1),
    )

    tipo_comida = fields.String(
        required=False,
        allow_none=True,
        validate=validate.OneOf(TIPOS_COMIDA),
    )

    page = fields.Integer(
        required=False,
        load_default=1,
        validate=validate.Range(min=1),
    )


class EntregaResumenFiltrosSchema(Schema):
    """Filtros para obtener el resumen de entregas."""

    fecha = fields.Date(
        required=False,
        allow_none=True,
    )

    sector_id = fields.Integer(
        required=False,
        allow_none=True,
        validate=validate.Range(min=1),
    )

    tipo_comida = fields.String(
        required=False,
        allow_none=True,
        validate=validate.OneOf(TIPOS_COMIDA),
    )

    @validates_schema
    def validar_filtros(self, data, **kwargs):
        if not data.get("fecha") and not data.get("tipo_comida"):
            raise ValidationError(
                "Debe indicar al menos fecha o tipo de comida."
            )


entrega_crear_schema = EntregaCrearSchema()
entrega_filtros_schema = EntregaFiltrosSchema()
entrega_resumen_filtros_schema = EntregaResumenFiltrosSchema()