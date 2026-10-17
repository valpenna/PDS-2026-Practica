import math
from flask import request
from sqlalchemy import func, select
from src.core.configuracion import Configuracion
from src.core.db import db


class PaginatedResult:
    def __init__(self, items, page, per_page, total_items):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total_items = total_items
        self.total_pages = math.ceil(total_items / per_page) if per_page > 0 else 1
        self.has_prev = page > 1
        self.has_next = page < self.total_pages
        self.prev_page = page - 1
        self.next_page = page + 1


def _obtener_parametros():
    """Lee la configuración global y el número de página solicitado."""
    config = Configuracion.obtener()
    per_page = config.elementos_por_pagina

    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    return page, per_page


def paginate_list(items: list) -> PaginatedResult:
    """Aplica la paginación global sobre una lista en memoria (mocks, CSVs, etc.)."""
    page, per_page = _obtener_parametros()
    total_items = len(items)

    inicio = (page - 1) * per_page
    fin = inicio + per_page
    items_pagina = items[inicio:fin]

    return PaginatedResult(
        items=items_pagina,
        page=page,
        per_page=per_page,
        total_items=total_items
    )


def paginate_query(query) -> PaginatedResult:
    """Aplica la paginación global sobre una consulta de SQLAlchemy."""
    page, per_page = _obtener_parametros()

    count_query = select(func.count()).select_from(query.subquery())
    total_items = db.session.scalar(count_query) or 0

    paginated_query = query.offset((page - 1) * per_page).limit(per_page)
    items = db.session.scalars(paginated_query).all()

    return PaginatedResult(
        items=items,
        page=page,
        per_page=per_page,
        total_items=total_items
    )