from suma import suma
from resta import resta
from multiplicacion import multiplicacion
from division import division
from validar_numero import operando_es_valido

print("Iniciando calculadora,por favor espere...")
print("Operaciones disponibles: ")
print("- Suma: +")
print("- Resta: -")
print("- Multiplicación: *")
print("- División: /")

operador = input("Ingrese la operación: ").strip()
operando_1 = input("Ingrese el primer operando: ")
operando_2 = input("Ingrese el segundo operando: ")


if not operando_es_valido(operando_1):
    print("El operando 1 es inválido: " + operando_1)
    exit(1)

if not operando_es_valido(operando_2):
    print("El operando 2 es inválido: " + operando_2)
    exit(1)

operando_1 = float(operando_1)
operando_2 = float(operando_2)

if operador == "+":
    resultado = suma(operando_1, operando_2)
    
elif operador == "-":
    resultado = resta(operando_1, operando_2)

elif operador == "*":
    resultado = multiplicacion(operando_1, operando_2)

elif operador == "/":
    try:
        resultado = division(operando_1, operando_2)
    except ZeroDivisionError as e:
        print(e)
        exit(1)

else:
    print("Operador desconocido")
    exit(1)

print("El resultado de la operación es: " + str(resultado))