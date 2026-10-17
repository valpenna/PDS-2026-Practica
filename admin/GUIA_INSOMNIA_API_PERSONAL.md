# Pruebas de la API de personal con Insomnia

Esta guía permite probar manualmente los endpoints de personal y la baja con
historial desde Insomnia.

## Antes de empezar

- Levantá Flask y la base de datos de **prueba**. Insomnia envía peticiones al
  servidor real; estas operaciones crean y modifican datos.
- Reemplazá `http://127.0.0.1:5000` si la aplicación usa otra dirección.
- Necesitás un usuario de **Servicio de Alimentación** y otro de **Jefe de
  Servicio**. El Jefe debe tener un sector asignado.
- En las URLs y JSON de ejemplo, reemplazá los IDs por los que devuelva tu
  sistema. Usá DNI nuevos para cada persona de prueba.

En requests protegidos, agregá estos headers:

```text
Authorization: Bearer TOKEN_DEL_USUARIO
Content-Type: application/json
```

## 1. Obtener tokens

Hacé un login por cada rol que vayas a probar.

**POST** `http://127.0.0.1:5000/api/auth/login`

```json
{
  "email": "EMAIL_DEL_USUARIO",
  "password": "CONTRASEÑA_DEL_USUARIO"
}
```

Copiá el campo `token` de la respuesta. Usá el token de Servicio de
Alimentación para gestionar personal y el de Jefe de Servicio para crear
pedidos y probar las restricciones por sector.

## 2. Consultar los IDs de catálogos

Con el token de Servicio de Alimentación:

- **GET** `/api/personnel-types`
- **GET** `/api/menu-types`
- **GET** `/api/sectors/`
- **GET** `/api/quotas?sector_id=ID_SECTOR&tipo_comida=almuerzo`

Los tres primeros devuelven listas con `id` y `nombre`. Para conocer el sector
del Jefe, usá su token en:

- **GET** `/api/auth/me`

La respuesta contiene el `sector_id` del Jefe. Si la consulta de cupos devuelve
uno para el sector y la comida elegidos, no hace falta crear otro.

## 3. Crear personas

### Personal Fijo

**POST** `/api/personnel`, con token de Servicio de Alimentación.

```json
{
  "dni": "90000001",
  "nombre": "Prueba",
  "apellido": "Personal",
  "tipo_personal_id": 1,
  "menu_id": 1,
  "sector_id": 3
}
```

Reemplazá `tipo_personal_id`, `menu_id` y `sector_id` por IDs existentes. La
respuesta esperada es `201`; guardá el `id` devuelto.

Un Jefe también puede crear Personal Fijo. En ese caso, el backend asigna el
sector del Jefe autenticado.

### Residente

**POST** `/api/personnel`, con token de Servicio de Alimentación.

```json
{
  "dni": "90000002",
  "nombre": "Prueba",
  "apellido": "Residente",
  "tipo_personal_id": 2,
  "menu_id": 1,
  "sector_id": null
}
```

La API guarda el sector como `null` para Residentes. La respuesta esperada es
`201`.

## 4. Probar listado, filtros y detalle

Con un token operativo:

- **GET** `/api/personnel?page=1&per_page=25`
- **GET** `/api/personnel?dni=90000001&page=1&per_page=25`
- **GET** `/api/personnel?nombre=Prueba&activo=true`
- **GET** `/api/personnel/ID_PERSONA`
- **GET** `/api/sectors/ID_SECTOR/personnel?page=1&per_page=25`

El listado devuelve `data`, `total`, `page` y `per_page`. Para un Jefe, el
backend limita los resultados a su sector y a Residentes; el listado por sector
solo le permite consultar su propio sector.

## 5. Probar actualización

**PUT** `/api/personnel/ID_PERSONA`, con token de Servicio de Alimentación.
El request debe incluir los campos requeridos aunque solo quieras modificar
algunos.

```json
{
  "dni": "90000001",
  "nombre": "Prueba",
  "apellido": "Personal",
  "tipo_personal_id": 2,
  "menu_id": 1,
  "sector_id": null,
  "activo": true
}
```

Este ejemplo cambia a la persona a Residente. La respuesta esperada es `200` y
su `sector` debe aparecer como `null`.

## 6. Probar errores y restricciones

- **Sin token:** repetí un GET de personal sin el header `Authorization`.
  Esperá `401`.
- **Rol no permitido:** usá un token de Administrador en un endpoint de
  personal. Esperá `403`.
- **Filtro inválido:** **GET** `/api/personnel?page=0`. Esperá `400`.
- **Persona inexistente:** **GET** `/api/personnel/999999`. Esperá `404`.
- **DNI duplicado:** repetí un POST de personal con un DNI ya registrado.
  Esperá `409`.
- **Jefe intenta crear un Residente:** usá el token de Jefe y un DNI nuevo.
  Esperá `403`. Usá un DNI nuevo porque la API comprueba primero si el DNI ya
  está registrado.
- **Jefe intenta consultar personal de otro sector:** probá el detalle o el
  listado por sector con un ID que no sea el suyo. Esperá `403`.
- **Jefe intenta modificar personal fuera de su sector o modificar un
  Residente:** usá el token de Jefe. Esperá `403`.

Los errores previstos de la API de personal devuelven JSON con un mensaje o
detalles de validación.

## 7. Preparar un cupo para crear un pedido

La creación del pedido necesita un cupo existente para el sector y el tipo de
comida. Si no hay uno, crealo con el token de Servicio de Alimentación:

**POST** `/api/quotas`

```json
{
  "sector_id": 3,
  "tipo_comida": "almuerzo",
  "cantidad_comensales": 20
}
```

Usá el `sector_id` del Jefe. Si ya existe un cupo para esa combinación,
consultalo con **GET** `/api/quotas?sector_id=3&tipo_comida=almuerzo` en vez de
crear un duplicado.

## 8. Crear un pedido que deje historial para una persona

Usá el token de Jefe de Servicio. La persona debe estar activa y ser Personal
Fijo de su sector o Residente. Elegí una fecha para la que no exista ya un pedido
en ese sector.

**POST** `/api/requests`

```json
{
  "periodicidad": "diaria",
  "fecha_desde": "2026-11-15",
  "fecha_hasta": "2026-11-15",
  "detalles": [
    {
      "person_id": 7,
      "tipo_comida": "almuerzo"
    }
  ]
}
```

Reemplazá `person_id` por el ID de la persona creada. La fecha debe tener formato
`YYYY-MM-DD`, estar libre para ese sector y contar con un cupo para almuerzo. La
respuesta esperada es `201`.

## 9. Probar las dos variantes de baja

### Persona con historial

Después de crear el pedido anterior, eliminá la persona con el token de Servicio
de Alimentación:

**DELETE** `/api/personnel/ID_PERSONA`

Esperá `200` y una respuesta con `"activo": false`. La persona queda inactiva
para conservar el historial.

### Persona sin historial

Crea otra persona con un DNI nuevo y **no** la incluyas en ningún pedido.
Eliminála con:

**DELETE** `/api/personnel/ID_PERSONA`

Esperá `200` y una respuesta con `"eliminada": true`. Si después consultás su
detalle, debería devolver `404`.
