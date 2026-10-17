from marshmallow import RAISE, Schema, ValidationError, fields, validate, validates_schema


class AutorizacionesFiltrosSchema(Schema):
    class Meta:
        unknown = RAISE

    fecha_desde = fields.Date()
    fecha_hasta = fields.Date()
    sector_id = fields.Integer(validate=validate.Range(min=1))
    tipo_comida = fields.String(
        validate=validate.OneOf(("desayuno", "almuerzo", "merienda", "cena"))
    )
    tipo_menu_id = fields.Integer(validate=validate.Range(min=1))
    estado = fields.String(
        validate=validate.OneOf(("confirmado", "autorizado", "rechazado"))
    )
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))

    @validates_schema
    def validar_rango(self, datos, **kwargs):
        if (
            datos.get("fecha_desde") is not None
            and datos.get("fecha_hasta") is not None
            and datos["fecha_desde"] > datos["fecha_hasta"]
        ):
            raise ValidationError(
                "fecha_hasta no puede ser anterior a fecha_desde.",
                field_name="fecha_hasta",
            )


autorizaciones_filtros_schema = AutorizacionesFiltrosSchema()


class AutorizacionSolicitudSchema(Schema):
    class Meta:
        unknown = RAISE

    id = fields.Integer(required=True, strict=True, validate=validate.Range(min=1))
    autorizada = fields.Boolean(required=True)


class AutorizarPedidoSchema(Schema):
    class Meta:
        unknown = RAISE

    solicitudes = fields.List(
        fields.Nested(AutorizacionSolicitudSchema),
        required=True,
        validate=validate.Length(min=1),
    )

    @validates_schema
    def validar_ids_unicos(self, datos, **kwargs):
        ids = [solicitud["id"] for solicitud in datos["solicitudes"]]
        if len(ids) != len(set(ids)):
            raise ValidationError("Los IDs de solicitudes no pueden repetirse.", field_name="solicitudes")


autorizar_pedido_schema = AutorizarPedidoSchema()