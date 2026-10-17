def division(operando_1, operando_2):
    if operando_2 == 0:
        raise ZeroDivisionError("No es posible dividir por cero.")
    return operando_1 / operando_2