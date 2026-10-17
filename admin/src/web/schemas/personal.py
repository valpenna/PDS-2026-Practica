from datetime import date

from marshmallow import Schema, fields, validate, RAISE


# Contratos de entrada para crear y editar personal
class PersonalEntradaSchema(Schema):
    """Contrato de entrada para crear Personal."""

    class Meta:
        unknown = RAISE  # Rechazo los campos que no estan definidos en el schema

    dni = fields.String(required=True, validate=validate.Length(min=7, max=12))
    nombre = fields.String(required=True, validate=validate.Length(min=2, max=50))
    apellido = fields.String(required=True, validate=validate.Length(min=2, max=50))
    tipo_personal_id = fields.Integer(required=True, validate=validate.Range(min=1))
    menu_id = fields.Integer(required=True, validate=validate.Range(min=1))
    sector_id = fields.Integer(
        required=False, allow_none=True, validate=validate.Range(min=1)
    )


class PersonalActualizacionSchema(PersonalEntradaSchema):
    """Contrato de entrada para editar Personal."""

    activo = fields.Boolean(required=False)


class PersonalSalidaSchema(Schema):
    """Contrato de salida de Personal (Para GET)"""

    id = fields.Integer(required=True)
    dni = fields.String(required=True)
    nombre = fields.String(required=True)
    apellido = fields.String(required=True)
    tipo_personal = fields.Nested(lambda: TipoPersonalSalidaSchema(), required=True)
    sector = fields.Nested(lambda: SectorSalidaSchema(), allow_none=True)
    tipo_menu = fields.Nested(lambda: TipoMenuSalidaSchema(), required=True)
    activo = fields.Boolean(required=True)


class PersonalFiltrarSchema(Schema):
    """Valida los filtros recibidos en la query string del listado."""

    class Meta:
        unknown = RAISE

    dni = fields.String(validate=validate.Length(min=1, max=12))
    nombre = fields.String(validate=validate.Length(min=1, max=50))
    apellido = fields.String(validate=validate.Length(min=1, max=50))
    sector_id = fields.Integer(validate=validate.Range(min=1))
    tipo_personal_id = fields.Integer(validate=validate.Range(min=1))
    activo = fields.Boolean(
        truthy={"true"},
        falsy={"false"},
        load_default=True,
    )
    pagina = fields.Integer(
        data_key="page",
        load_default=1,
        validate=validate.Range(min=1),
    )
    por_pagina = fields.Integer(
        data_key="per_page",
        load_default=25,
        validate=validate.Range(min=1, max=25),
    )


class PersonalSectorQuerySchema(Schema):
    """Valida fecha y paginacion del listado de personal por sector."""

    class Meta:
        unknown = RAISE

    fecha = fields.Date(load_default=date.today)
    pagina = fields.Integer(
        data_key="page",
        load_default=1,
        validate=validate.Range(min=1),
    )
    por_pagina = fields.Integer(
        data_key="per_page",
        load_default=25,
        validate=validate.Range(min=1, max=25),
    )


class TipoPersonalSalidaSchema(Schema):
    """Contrato para la salida de Tipo Personal"""

    id = fields.Integer(required=True)
    nombre = fields.String(required=True)


class SectorSalidaSchema(Schema):
    """Contrato para la salida de Sector"""

    id = fields.Integer(required=True)
    nombre = fields.String(required=True)


class TipoMenuSalidaSchema(Schema):
    """Contrato para la salida de Tipo menu"""

    id = fields.Integer(required=True)
    nombre = fields.String(required=True)


personal_entrada_schema = PersonalEntradaSchema()
personal_actualizacion_schema = PersonalActualizacionSchema()
personal_salida_schema = PersonalSalidaSchema()
personal_filtrar_schema = PersonalFiltrarSchema()
personal_sector_query_schema = PersonalSectorQuerySchema()
