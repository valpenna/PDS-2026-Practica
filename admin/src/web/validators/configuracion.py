def validar_configuracion(elementos_str: str, sitio_en_mantenimiento: bool, mensaje_mantenimiento: str) -> list[str]:
    errores = []
    
    # Validar que sea dígito y esté entre 1 y 25
    if not elementos_str.isdigit() or not (1 <= int(elementos_str) <= 25):
        errores.append("La cantidad de elementos por página debe ser un número entero entre 1 y 25.")

    if sitio_en_mantenimiento and not mensaje_mantenimiento:
        errores.append("Debe especificar un mensaje descriptivo si activa el modo mantenimiento.")
    return errores