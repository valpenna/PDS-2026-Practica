from marshmallow import RAISE, Schema, fields, validate


class CupoCrearSchema(Schema):
    class Meta:
        unknown = RAISE

    sector_id = fields.Integer(required=True, strict=True, validate=validate.Range(min=1))
    tipo_comida = fields.String(required=True, validate=validate.OneOf(("desayuno", "almuerzo", "merienda", "cena")))
    cantidad_comensales = fields.Integer(required=True, strict=True, validate=validate.Range(min=1))


class CupoListadoSchema(Schema):
    id = fields.Integer()
    sector_id = fields.Integer()
    tipo_comida = fields.String()
    cantidad_comensales = fields.Integer()


class CupoDetalleSchema(CupoListadoSchema):
    fecha_creacion = fields.DateTime()
    fecha_modificacion = fields.DateTime()


class CupoFiltrosSchema(Schema):
    class Meta:
        unknown = RAISE

    sector_id = fields.Integer(validate=validate.Range(min=1))
    tipo_comida = fields.String(validate=validate.OneOf(("desayuno", "almuerzo", "merienda", "cena")))
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    sort = fields.String(load_default="id", validate=validate.OneOf(("id", "sector")))


cupo_crear_schema = CupoCrearSchema()
cupo_salida_schema = CupoListadoSchema()
cupo_listado_schema = CupoListadoSchema(many=True)
cupo_detalle_schema = CupoDetalleSchema()
cupo_filtros_schema = CupoFiltrosSchema()