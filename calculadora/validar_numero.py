def operando_es_valido(operando):
    try:
        float(operando)
        return True
    except ValueError:
        return False