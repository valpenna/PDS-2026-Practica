import unicodedata

def normalizar_texto(texto: str) -> str:
    """Convierte a minúsculas y quita tildes y espacios."""
    if not texto or not isinstance(texto, str):
        return ""
    texto_descompuesto = unicodedata.normalize("NFD", " ".join(texto.lower().split()))
    return "".join(c for c in texto_descompuesto if unicodedata.category(c) != "Mn")