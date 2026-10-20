"""Motor de generación de números pseudoaleatorios.

Toda la lógica se implementa con aritmética entera y funciones propias.
No se importa la biblioteca ``random`` ni ningún paquete externo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------


class ErrorGeneracion(ValueError):
    """Error de validación con un mensaje pensado para mostrarse en la UI."""

    def __init__(self, mensaje: str, campo: Optional[str] = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campo = campo


@dataclass(frozen=True)
class Campo:
    clave: str
    etiqueta: str
    defecto: int
    ayuda: str
    minimo: int = 0
    maximo: Optional[int] = None


@dataclass(frozen=True)
class Metodo:
    id: str
    nombre: str
    categoria: str
    resumen: str
    formula: str
    descripcion: str
    idea: str
    pasos: tuple[str, ...]
    condiciones: tuple[str, ...]
    campos: tuple[Campo, ...]
    ejemplo: dict[str, int]
    fuente: str


@dataclass
class Paso:
    indice: int
    notacion: str
    valor: int
    u: float
    formula: str
    detalle: list[tuple[str, str]]
    nota: str = ""


@dataclass
class Resultado:
    metodo: Metodo
    parametros: dict[str, int]
    semillas: list[int]
    pasos: list[Paso]
    advertencias: list[str]
    periodo: Optional[int]
    inicio_periodo: Optional[int]
    periodo_teorico: Optional[int]
    periodo_exacto: bool
    cantidad: int
    decimales: int
    denominador: int

    @property
    def valores_x(self) -> list[int]:
        return [paso.valor for paso in self.pasos]

    @property
    def valores_u(self) -> list[float]:
        return [paso.u for paso in self.pasos]


@dataclass
class Estadisticas:
    media: float
    varianza: float
    desviacion: float
    minimo: float
    maximo: float


# ---------------------------------------------------------------------------
# Catálogo de métodos
# ---------------------------------------------------------------------------

METODOS: tuple[Metodo, ...] = (
    Metodo(
        id="cuadrados_medios",
        nombre="Cuadrados medios",
        categoria="CLÁSICOS",
        resumen="Von Neumann · 1946",
        formula="xₙ = centro_d(xₙ₋₁²)      Uₙ = xₙ / 10^d",
        descripcion=(
            "El método clásico de von Neumann: eleva la semilla al cuadrado y "
            "conserva los dígitos del centro para obtener el siguiente estado."
        ),
        idea=(
            "Al elevar al cuadrado, los dígitos de la semilla se mezclan. Los "
            "dígitos centrales cambian de forma menos predecible que los extremos; "
            "al dividirlos entre 10^d se obtiene un valor en [0, 1)."
        ),
        pasos=(
            "Fija d (par) y una semilla x₀ de hasta d dígitos.",
            "Eleva x₀ al cuadrado y escribe el resultado con 2d dígitos, rellenando con ceros a la izquierda.",
            "Toma los d dígitos centrales: ese es x₁.",
            "Normaliza: U₁ = x₁ / 10^d.",
            "Repite el proceso con x₁ para obtener x₂, x₃, …",
        ),
        condiciones=(
            "d debe ser par para que exista un centro único.",
            "Puede llegar a 0 o a un ciclo muy corto; no se recomienda para aplicaciones reales.",
            "El periodo máximo posible es 10^d, pero casi nunca se alcanza.",
        ),
        campos=(
            Campo("d", "Dígitos centrales (d)", 4, "Par: 2, 4, 6 u 8.", 2, 8),
            Campo("x0", "Semilla x₀", 1234, "Entre 0 y 10^d − 1.", 0, 99_999_999),
        ),
        ejemplo={"d": 4, "x0": 1234},
        fuente="von Neumann (1946). Método clásico descrito en la literatura de simulación.",
    ),
    Metodo(
        id="productos_medios",
        nombre="Productos medios",
        categoria="CLÁSICOS",
        resumen="Dos semillas · producto",
        formula="xₙ = centro_d(xₙ₋₂ · xₙ₋₁)      Uₙ = xₙ / 10^d",
        descripcion=(
            "Variante del cuadrado medio: en lugar de elevar una semilla al "
            "cuadrado, multiplica los dos estados anteriores y toma el centro."
        ),
        idea=(
            "El producto de dos números de d dígitos tiene hasta 2d dígitos. "
            "Su parte central combina información de ambos estados y alimenta "
            "la siguiente multiplicación."
        ),
        pasos=(
            "Fija d (par) y dos semillas x₀ y x₁ de hasta d dígitos.",
            "Multiplica x₀ · x₁ y escribe el producto con 2d dígitos.",
            "Toma los d dígitos centrales: ese es x₂.",
            "Normaliza: U₁ = x₂ / 10^d.",
            "Repite con las dos últimas semillas: x₃ = centro(x₁ · x₂), etc.",
        ),
        condiciones=(
            "Necesita dos semillas iniciales; no se puede arrancar con una sola.",
            "Al igual que el cuadrado medio, puede degenerar en 0 o en ciclos cortos.",
            "El número de pares posibles es 10^(2d), una cota muy optimista del periodo.",
        ),
        campos=(
            Campo("d", "Dígitos centrales (d)", 4, "Par: 2, 4, 6 u 8.", 2, 8),
            Campo("x0", "Semilla x₀", 1234, "Entre 0 y 10^d − 1.", 0, 99_999_999),
            Campo("x1", "Semilla x₁", 5678, "Entre 0 y 10^d − 1.", 0, 99_999_999),
        ),
        ejemplo={"d": 4, "x0": 1234, "x1": 5678},
        fuente="Método clásico de productos medios, pariente del cuadrado medio de von Neumann.",
    ),
    Metodo(
        id="constante_aditiva",
        nombre="Constante aditiva",
        categoria="CLÁSICOS",
        resumen="Suma un paso fijo",
        formula="xₙ = (xₙ₋₁ + c) mod m      Uₙ = xₙ / m",
        descripcion=(
            "El generador más simple: a cada estado se le suma una constante c "
            "y se conserva el resto de dividir entre m."
        ),
        idea=(
            "La suma recorre los residuos módulo m. Si c y m son coprimos, la "
            "sucesión pasa por todos los residuos antes de repetirse."
        ),
        pasos=(
            "Elige el módulo m, la constante c y la semilla x₀.",
            "Suma c al estado anterior: s = xₙ₋₁ + c.",
            "Calcula el resto de s entre m: xₙ = s mod m.",
            "Normaliza: Uₙ = xₙ / m.",
            "Repite desde el paso 2.",
        ),
        condiciones=(
            "Si mcd(c, m) = 1, el periodo es exactamente m.",
            "Si c y m comparten factores, el periodo se acorta.",
            "Es determinista y muy fácil de predecir; útil para aprender, no para simular.",
        ),
        campos=(
            Campo("m", "Módulo m", 100, "Mayor que 1.", 2, 1_000_000_000),
            Campo("c", "Constante c", 37, "Entero positivo.", 1, 1_000_000_000),
            Campo("x0", "Semilla x₀", 42, "Entre 0 y m − 1.", 0, 1_000_000_000),
        ),
        ejemplo={"m": 100, "c": 37, "x0": 42},
        fuente="Caso particular aditivo del generador congruencial lineal.",
    ),
    Metodo(
        id="congruencial_lineal",
        nombre="Congruencial lineal",
        categoria="CONGRUENCIALES",
        resumen="Mixto · a, c y m",
        formula="xₙ = (a·xₙ₋₁ + c) mod m      Uₙ = xₙ / m",
        descripcion=(
            "El generador congruencial mixto: combina una multiplicación y una "
            "suma, y reduce el resultado módulo m."
        ),
        idea=(
            "La multiplicación dispersa el estado y la suma evita que se quede "
            "en un patrón demasiado simple. El módulo mantiene los valores en "
            "un rango finito de m estados posibles."
        ),
        pasos=(
            "Elige a (multiplicador), c (incremento), m (módulo) y x₀ (semilla).",
            "Calcula el producto a · xₙ₋₁.",
            "Súmale c: s = a · xₙ₋₁ + c.",
            "Divide s entre m y toma el resto: xₙ = s mod m.",
            "Normaliza: Uₙ = xₙ / m.",
        ),
        condiciones=(
            "Periodo completo m si se cumplen las condiciones de Hull–Dobell:",
            "mcd(c, m) = 1; todo factor primo de m divide a (a − 1);",
            "si m es divisible entre 4, entonces (a − 1) también.",
            "Con m = 2^b suele ser eficiente en computadoras, pero los bits bajos se correlacionan.",
        ),
        campos=(
            Campo("a", "Multiplicador a", 21, "Entero positivo.", 1, 1_000_000_000),
            Campo("c", "Incremento c", 17, "Entero no negativo.", 0, 1_000_000_000),
            Campo("m", "Módulo m", 100, "Mayor que 1.", 2, 2_147_483_647),
            Campo("x0", "Semilla x₀", 13, "Entre 0 y m − 1.", 0, 2_147_483_646),
        ),
        ejemplo={"a": 21, "c": 17, "m": 100, "x0": 13},
        fuente="Ross, Simulación (2.ª ed.), §3.1; Coss Bu, Simulación, cap. 2.",
    ),
    Metodo(
        id="congruencial_multiplicativo",
        nombre="Congruencial multiplicativo",
        categoria="CONGRUENCIALES",
        resumen="Lehmer · sin incremento",
        formula="xₙ = (a·xₙ₋₁) mod m      Uₙ = xₙ / m",
        descripcion=(
            "El generador de Lehmer: como el congruencial lineal, pero sin "
            "término aditivo (c = 0)."
        ),
        idea=(
            "Sin suma, el estado siempre se multiplica por la misma constante. "
            "Si m es primo y a es una raíz primitiva, la sucesión recorre todos "
            "los residuos no nulos antes de repetirse."
        ),
        pasos=(
            "Elige un módulo m (preferiblemente primo), un multiplicador a y una semilla x₀ ≠ 0.",
            "Multiplica: p = a · xₙ₋₁.",
            "Divide p entre m y toma el resto: xₙ = p mod m.",
            "Normaliza: Uₙ = xₙ / m.",
            "Repite desde el paso 2.",
        ),
        condiciones=(
            "La semilla debe ser coprima con m; si m es primo, basta con x₀ ≠ 0.",
            "El periodo máximo es m − 1, y se alcanza si m es primo y a es raíz primitiva.",
            "No conviene usar m = 2^b: el bit menos significativo tiene un patrón muy corto.",
        ),
        campos=(
            Campo("a", "Multiplicador a", 5, "Entero positivo.", 1, 1_000_000_000),
            Campo("m", "Módulo m", 97, "Primo, mayor que 1.", 2, 2_147_483_647),
            Campo("x0", "Semilla x₀", 7, "Coprima con m, distinta de 0.", 1, 2_147_483_646),
        ),
        ejemplo={"a": 5, "m": 97, "x0": 7},
        fuente="Lehmer (1949); Ross, Simulación (2.ª ed.), §3.1.",
    ),
    Metodo(
        id="congruencial_aditivo",
        nombre="Congruencial aditivo",
        categoria="CONGRUENCIALES",
        resumen="Fibonacci · dos semillas",
        formula="xₙ = (xₙ₋₁ + xₙ₋₂) mod m      Uₙ = xₙ / m",
        descripcion=(
            "Generador tipo Fibonacci: cada estado es la suma de los dos "
            "anteriores, reducida módulo m."
        ),
        idea=(
            "La dependencia de dos estados anteriores alarga el patrón y evita "
            "la degeneración típica de una sola semilla. Es la base de los "
            "generadores aditivos modernos."
        ),
        pasos=(
            "Elige el módulo m y dos semillas x₀ y x₁.",
            "Suma los dos estados anteriores: s = xₙ₋₂ + xₙ₋₁.",
            "Toma el resto de s entre m: xₙ = s mod m.",
            "Normaliza: Uₙ = xₙ / m.",
            "Desplaza las semillas y repite.",
        ),
        condiciones=(
            "Necesita dos semillas; si ambas son 0, la sucesión se queda en 0.",
            "El periodo depende de m y de las semillas; puede ser largo, pero no se garantiza.",
            "La cota teórica de estados es m², porque el estado es el par (xₙ₋₁, xₙ).",
        ),
        campos=(
            Campo("m", "Módulo m", 100, "Mayor que 1.", 2, 1_000_000_000),
            Campo("x0", "Semilla x₀", 37, "Entre 0 y m − 1.", 0, 1_000_000_000),
            Campo("x1", "Semilla x₁", 84, "Entre 0 y m − 1.", 0, 1_000_000_000),
        ),
        ejemplo={"m": 100, "x0": 37, "x1": 84},
        fuente="Generador aditivo de Fibonacci, familia de los congruenciales múltiples.",
    ),
    Metodo(
        id="congruencial_cuadratico",
        nombre="Congruencial cuadrático",
        categoria="CONGRUENCIALES",
        resumen="Término x² · no lineal",
        formula="xₙ = (a·xₙ₋₁² + b·xₙ₋₁ + c) mod m",
        descripcion=(
            "Añade un término cuadrático a la recurrencia. La no linealidad "
            "dificulta ver patrones, a costa de un comportamiento más difícil "
            "de analizar."
        ),
        idea=(
            "El término x² introduce una mezcla no lineal; los otros términos "
            "desplazan y modulan el resultado. El módulo mantiene el estado "
            "dentro de un conjunto finito."
        ),
        pasos=(
            "Elige a, b, c, m y la semilla x₀.",
            "Calcula xₙ₋₁², multiplícalo por a y suma b · xₙ₋₁.",
            "Suma c: s = a·xₙ₋₁² + b·xₙ₋₁ + c.",
            "Toma el resto de s entre m: xₙ = s mod m.",
            "Normaliza: Uₙ = xₙ / m y repite.",
        ),
        condiciones=(
            "No existen condiciones sencillas que garanticen periodo máximo.",
            "Puede caer en ciclos cortos o en puntos fijos; revisa siempre el periodo observado.",
            "El máximo teórico de estados distintos es m.",
        ),
        campos=(
            Campo("a", "Coeficiente a", 3, "Entero positivo.", 1, 1_000_000),
            Campo("b", "Coeficiente b", 7, "Entero no negativo.", 0, 1_000_000),
            Campo("c", "Constante c", 11, "Entero no negativo.", 0, 1_000_000),
            Campo("m", "Módulo m", 100, "Mayor que 1.", 2, 1_000_000_000),
            Campo("x0", "Semilla x₀", 13, "Entre 0 y m − 1.", 0, 1_000_000_000),
        ),
        ejemplo={"a": 3, "b": 7, "c": 11, "m": 100, "x0": 13},
        fuente="Generador congruencial de segundo orden, extensión no lineal del LCG.",
    ),
)

METODOS_POR_ID = {metodo.id: metodo for metodo in METODOS}


# ---------------------------------------------------------------------------
# Utilidades aritméticas propias
# ---------------------------------------------------------------------------


def mcd(a: int, b: int) -> int:
    """Máximo común divisor por el algoritmo de Euclides."""
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def factores_primos(n: int) -> list[int]:
    """Factores primos distintos de n, sin usar librerías externas."""
    factores: list[int] = []
    if n % 2 == 0:
        factores.append(2)
        while n % 2 == 0:
            n //= 2
    divisor = 3
    while divisor * divisor <= n:
        if n % divisor == 0:
            factores.append(divisor)
            while n % divisor == 0:
                n //= divisor
        divisor += 2
    if n > 1:
        factores.append(n)
    return factores


def es_primo(n: int) -> bool:
    """Prueba de primalidad por división hasta la raíz cuadrada."""
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    divisor = 5
    while divisor * divisor <= n:
        if n % divisor == 0 or n % (divisor + 2) == 0:
            return False
        divisor += 6
    return True


def es_raiz_primitiva(a: int, p: int) -> bool:
    """Comprueba si a genera todo el grupo multiplicativo módulo p (p primo)."""
    if p == 2:
        return a % p == 1
    if mcd(a, p) != 1:
        return False
    for factor in factores_primos(p - 1):
        if pow(a, (p - 1) // factor, p) == 1:
            return False
    return True


def cumple_hull_dobell(a: int, c: int, m: int) -> bool:
    """Condiciones de Hull–Dobell para periodo completo de un LCG mixto."""
    if m < 2 or mcd(c, m) != 1:
        return False
    if any((a - 1) % factor != 0 for factor in factores_primos(m)):
        return False
    if m % 4 == 0 and (a - 1) % 4 != 0:
        return False
    return True


# ---------------------------------------------------------------------------
# Formato y ayudas de presentación
# ---------------------------------------------------------------------------


_SUBINDICES = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def subindice(n: int) -> str:
    return "x" + str(n).translate(_SUBINDICES)


def notacion_de_paso(resultado: "Resultado", paso: int) -> str:
    """Notación del estado que corresponde al paso generado (1-based).

    Los métodos de dos semillas producen x₂ en el primer paso; los demás
    producen x₁.
    """
    desplazamiento = (
        1
        if resultado.metodo.id in ("productos_medios", "congruencial_aditivo")
        else 0
    )
    return subindice(paso + desplazamiento)


def formato_entero(n: int) -> str:
    """Separador de miles con punto, sin depender de la configuración local."""
    return f"{n:,}".replace(",", ".")


def formato_u(valor: float, decimales: int = 6) -> str:
    """Número uniforme con coma decimal, como se usa en español."""
    return f"{valor:.{decimales}f}".replace(".", ",")


# ---------------------------------------------------------------------------
# Lectura y validación de parámetros
# ---------------------------------------------------------------------------


def _a_entero(valor: object, etiqueta: str, campo: Optional[str] = None) -> int:
    if isinstance(valor, bool):
        raise ErrorGeneracion(f"«{etiqueta}» debe ser un número entero.", campo)
    if isinstance(valor, int):
        return valor
    texto = str(valor).strip()
    if not texto:
        raise ErrorGeneracion(f"«{etiqueta}» no puede estar vacío.", campo)
    if not texto.isdigit():
        raise ErrorGeneracion(
            f"«{etiqueta}» debe ser un número entero no negativo (sin separadores ni signos).",
            campo,
        )
    return int(texto)


def _leer_campo(valores: dict[str, object], campo: Campo) -> int:
    valor = _a_entero(valores.get(campo.clave, campo.defecto), campo.etiqueta, campo.clave)
    if valor < campo.minimo:
        raise ErrorGeneracion(
            f"«{campo.etiqueta}» debe ser mayor o igual que {formato_entero(campo.minimo)}.",
            campo.clave,
        )
    if campo.maximo is not None and valor > campo.maximo:
        raise ErrorGeneracion(
            f"«{campo.etiqueta}» debe ser menor o igual que {formato_entero(campo.maximo)}.",
            campo.clave,
        )
    return valor


def _validar_rango(valor: int, etiqueta: str, minimo: int, maximo: int, clave: str) -> None:
    if valor < minimo or valor > maximo:
        if minimo == maximo:
            detalle = f"debe ser exactamente {formato_entero(minimo)}"
        else:
            detalle = (
                f"debe estar entre {formato_entero(minimo)} y "
                f"{formato_entero(maximo)}"
            )
        raise ErrorGeneracion(f"«{etiqueta}» {detalle}.", clave)


def _validar_semilla(x0: int, m: int, etiqueta: str = "Semilla x₀") -> None:
    _validar_rango(x0, etiqueta, 0, m - 1, "x0")


# ---------------------------------------------------------------------------
# Detectores y avisos
# ---------------------------------------------------------------------------


def _detectar_periodo(estados: list[object]) -> tuple[Optional[int], Optional[int]]:
    """Devuelve (longitud del ciclo, primer índice del ciclo) si se repite."""
    vistos: dict[object, int] = {}
    for indice, estado in enumerate(estados):
        if estado in vistos:
            inicio = vistos[estado]
            return indice - inicio, inicio + 1
        vistos[estado] = indice
    return None, None


def _aviso_ciclo(
    advertencias: list[str],
    periodo: Optional[int],
    inicio: Optional[int],
    notacion_inicio: str,
) -> None:
    if periodo is None or inicio is None:
        return
    if periodo == 1:
        advertencias.append(
            f"El generador quedó fijo en {notacion_inicio}: todos los valores siguientes son iguales."
        )
    else:
        advertencias.append(
            f"Se detectó un ciclo de longitud {periodo} a partir de {notacion_inicio}; "
            "los valores se repiten."
        )


def _cota_periodo(metodo_id: str, parametros: dict[str, int]) -> Optional[int]:
    if metodo_id == "cuadrados_medios":
        return 10 ** parametros["d"]
    if metodo_id == "productos_medios":
        return 10 ** (2 * parametros["d"])
    if metodo_id == "constante_aditiva":
        return parametros["m"]
    if metodo_id == "congruencial_lineal":
        return parametros["m"]
    if metodo_id == "congruencial_multiplicativo":
        return parametros["m"] - 1
    if metodo_id == "congruencial_aditivo":
        return parametros["m"] * parametros["m"]
    if metodo_id == "congruencial_cuadratico":
        return parametros["m"]
    return None


# ---------------------------------------------------------------------------
# Generación
# ---------------------------------------------------------------------------


def generar(
    metodo_id: str,
    valores: dict[str, object],
    cantidad: object = 12,
    decimales: object = 6,
) -> Resultado:
    """Genera la secuencia del método indicado.

    ``valores`` contiene los campos propios del método. ``cantidad`` y
    ``decimales`` son comunes a todos los métodos.
    """
    metodo = METODOS_POR_ID.get(metodo_id)
    if metodo is None:
        raise ErrorGeneracion("El método seleccionado no existe.", "metodo")

    n = _a_entero(cantidad, "Cantidad de números", "cantidad")
    if n < 1 or n > 100:
        raise ErrorGeneracion("«Cantidad de números» debe estar entre 1 y 100.", "cantidad")

    dec = _a_entero(decimales, "Decimales de U", "decimales")
    if dec < 2 or dec > 8:
        raise ErrorGeneracion("«Decimales de U» debe estar entre 2 y 8.", "decimales")

    parametros = {campo.clave: _leer_campo(valores, campo) for campo in metodo.campos}
    advertencias: list[str] = []

    if metodo_id == "cuadrados_medios":
        resultado = _cuadrados_medios(parametros, n, dec, advertencias)
    elif metodo_id == "productos_medios":
        resultado = _productos_medios(parametros, n, dec, advertencias)
    elif metodo_id == "constante_aditiva":
        resultado = _constante_aditiva(parametros, n, dec, advertencias)
    elif metodo_id == "congruencial_lineal":
        resultado = _congruencial_lineal(parametros, n, dec, advertencias)
    elif metodo_id == "congruencial_multiplicativo":
        resultado = _congruencial_multiplicativo(parametros, n, dec, advertencias)
    elif metodo_id == "congruencial_aditivo":
        resultado = _congruencial_aditivo(parametros, n, dec, advertencias)
    elif metodo_id == "congruencial_cuadratico":
        resultado = _congruencial_cuadratico(parametros, n, dec, advertencias)
    else:  # pragma: no cover - protegido por el catálogo
        raise ErrorGeneracion("Método no implementado.", "metodo")

    resultado.metodo = metodo
    resultado.cantidad = n
    resultado.decimales = dec
    return resultado


def _base(
    metodo_id: str,
    parametros: dict[str, int],
    semillas: list[int],
    pasos: list[Paso],
    advertencias: list[str],
    periodo: Optional[int],
    inicio: Optional[int],
    exacto: bool,
    denominador: int,
) -> Resultado:
    metodo = METODOS_POR_ID[metodo_id]
    return Resultado(
        metodo=metodo,
        parametros=parametros,
        semillas=semillas,
        pasos=pasos,
        advertencias=advertencias,
        periodo=periodo,
        inicio_periodo=inicio,
        periodo_teorico=_cota_periodo(metodo_id, parametros),
        periodo_exacto=exacto,
        cantidad=len(pasos),
        decimales=6,
        denominador=denominador,
    )


def _cuadrados_medios(
    p: dict[str, int], n: int, dec: int, advertencias: list[str]
) -> Resultado:
    d = p["d"]
    if d % 2 != 0:
        raise ErrorGeneracion("«Dígitos centrales (d)» debe ser un número par.", "d")
    _validar_rango(d, "Dígitos centrales (d)", 2, 8, "d")
    limite = 10 ** d
    _validar_rango(p["x0"], "Semilla x₀", 0, limite - 1, "x0")

    x = p["x0"]
    pasos: list[Paso] = []
    estados: list[int] = []
    cero_avisado = False

    for indice in range(1, n + 1):
        cuadrado = x * x
        cuadrado_txt = f"{cuadrado:0{2 * d}d}"
        centro_txt = cuadrado_txt[d // 2 : d // 2 + d]
        siguiente = int(centro_txt)
        u = siguiente / limite
        formula = f"{subindice(indice)} = centro_{d}({subindice(indice - 1)}²)"
        detalle = [
            ("Cuadrado", f"{formato_entero(x)}² = {formato_entero(cuadrado)}"),
            ("Relleno a 2d dígitos", cuadrado_txt),
            ("Dígitos centrales", f"[{centro_txt}] → {formato_entero(siguiente)}"),
            ("Normalización", f"{formato_entero(siguiente)} / {formato_entero(limite)} = {formato_u(u, dec)}"),
        ]
        nota = ""
        if siguiente == 0:
            nota = "El estado llegó a 0: es un punto fijo y la secuencia ya no cambia."
            if not cero_avisado:
                advertencias.append(
                    "La secuencia llegó a 0. En los cuadrados medios, 0 es un punto fijo."
                )
                cero_avisado = True
        pasos.append(Paso(indice, subindice(indice), siguiente, u, formula, detalle, nota))
        estados.append(siguiente)
        x = siguiente

    periodo, inicio = _detectar_periodo(estados)
    if inicio is not None:
        _aviso_ciclo(advertencias, periodo, inicio, subindice(inicio))
    return _base(
        "cuadrados_medios", p, [p["x0"]], pasos, advertencias, periodo, inicio, False, limite
    )


def _productos_medios(
    p: dict[str, int], n: int, dec: int, advertencias: list[str]
) -> Resultado:
    d = p["d"]
    if d % 2 != 0:
        raise ErrorGeneracion("«Dígitos centrales (d)» debe ser un número par.", "d")
    _validar_rango(d, "Dígitos centrales (d)", 2, 8, "d")
    limite = 10 ** d
    _validar_rango(p["x0"], "Semilla x₀", 0, limite - 1, "x0")
    _validar_rango(p["x1"], "Semilla x₁", 0, limite - 1, "x1")
    if p["x0"] == 0 and p["x1"] == 0:
        raise ErrorGeneracion("Las dos semillas no pueden ser 0 al mismo tiempo.", "x1")

    x_anterior, x_actual = p["x0"], p["x1"]
    pasos: list[Paso] = []
    estados: list[tuple[int, int]] = []
    cero_avisado = False

    for indice in range(1, n + 1):
        producto = x_anterior * x_actual
        producto_txt = f"{producto:0{2 * d}d}"
        centro_txt = producto_txt[d // 2 : d // 2 + d]
        siguiente = int(centro_txt)
        u = siguiente / limite
        formula = (
            f"{subindice(indice + 1)} = centro_{d}"
            f"({subindice(indice - 1)} · {subindice(indice)})"
        )
        detalle = [
            ("Producto", f"{formato_entero(x_anterior)} · {formato_entero(x_actual)} = {formato_entero(producto)}"),
            ("Relleno a 2d dígitos", producto_txt),
            ("Dígitos centrales", f"[{centro_txt}] → {formato_entero(siguiente)}"),
            ("Normalización", f"{formato_entero(siguiente)} / {formato_entero(limite)} = {formato_u(u, dec)}"),
        ]
        nota = ""
        if siguiente == 0 and not cero_avisado:
            nota = "El estado llegó a 0; revisa si la secuencia sigue aportando valores."
            advertencias.append(
                "La secuencia llegó a 0. En los productos medios suele iniciar una degeneración."
            )
            cero_avisado = True
        pasos.append(
            Paso(indice, subindice(indice + 1), siguiente, u, formula, detalle, nota)
        )
        estados.append((x_anterior, x_actual))
        x_anterior, x_actual = x_actual, siguiente

    periodo, inicio = _detectar_periodo(estados)
    if inicio is not None:
        _aviso_ciclo(advertencias, periodo, inicio, subindice(inicio + 1))
    return _base(
        "productos_medios",
        p,
        [p["x0"], p["x1"]],
        pasos,
        advertencias,
        periodo,
        inicio,
        False,
        limite,
    )


def _constante_aditiva(
    p: dict[str, int], n: int, dec: int, advertencias: list[str]
) -> Resultado:
    m = p["m"]
    _validar_rango(m, "Módulo m", 2, 1_000_000_000, "m")
    _validar_semilla(p["x0"], m)
    c = p["c"]
    if mcd(c, m) != 1:
        advertencias.append(
            "c y m no son coprimos: el periodo será menor que m. "
            "Para recorrer todos los residuos, elige mcd(c, m) = 1."
        )

    x = p["x0"]
    pasos: list[Paso] = []
    estados: list[int] = []
    for indice in range(1, n + 1):
        suma = x + c
        cociente, resto = divmod(suma, m)
        u = resto / m
        formula = f"{subindice(indice)} = ({subindice(indice - 1)} + {formato_entero(c)}) mod {formato_entero(m)}"
        detalle = [
            ("Suma", f"{formato_entero(x)} + {formato_entero(c)} = {formato_entero(suma)}"),
            ("División entera", f"{formato_entero(suma)} ÷ {formato_entero(m)} = {formato_entero(cociente)}"),
            ("Resto", f"{formato_entero(suma)} − {formato_entero(cociente)} · {formato_entero(m)} = {formato_entero(resto)}"),
            ("Normalización", f"{formato_entero(resto)} / {formato_entero(m)} = {formato_u(u, dec)}"),
        ]
        pasos.append(Paso(indice, subindice(indice), resto, u, formula, detalle))
        estados.append(resto)
        x = resto

    periodo, inicio = _detectar_periodo(estados)
    if inicio is not None:
        _aviso_ciclo(advertencias, periodo, inicio, subindice(inicio))
    exacto = mcd(c, m) == 1
    if exacto and periodo is None:
        advertencias.append(
            f"Con mcd(c, m) = 1 el periodo es {formato_entero(m)}; "
            f"no se repite dentro de los primeros {n} valores."
        )
    return _base(
        "constante_aditiva", p, [p["x0"]], pasos, advertencias, periodo, inicio, exacto, m
    )


def _congruencial_lineal(
    p: dict[str, int], n: int, dec: int, advertencias: list[str]
) -> Resultado:
    a, c, m, x0 = p["a"], p["c"], p["m"], p["x0"]
    _validar_rango(m, "Módulo m", 2, 2_147_483_647, "m")
    _validar_semilla(x0, m)

    completo = cumple_hull_dobell(a, c, m)
    if not completo:
        advertencias.append(
            "Los parámetros no cumplen las condiciones de Hull–Dobell; "
            "el periodo puede ser menor que m."
        )
    if c == 0:
        advertencias.append(
            "Con c = 0 este generador se comporta como un congruencial multiplicativo."
        )

    x = x0
    pasos: list[Paso] = []
    estados: list[int] = []
    for indice in range(1, n + 1):
        producto = a * x
        total = producto + c
        cociente, resto = divmod(total, m)
        u = resto / m
        formula = (
            f"{subindice(indice)} = ({formato_entero(a)}·{subindice(indice - 1)}"
            f" + {formato_entero(c)}) mod {formato_entero(m)}"
        )
        detalle = [
            ("Producto", f"{formato_entero(a)} · {formato_entero(x)} = {formato_entero(producto)}"),
            ("Suma", f"{formato_entero(producto)} + {formato_entero(c)} = {formato_entero(total)}"),
            ("División entera", f"{formato_entero(total)} ÷ {formato_entero(m)} = {formato_entero(cociente)}"),
            ("Resto", f"{formato_entero(total)} − {formato_entero(cociente)} · {formato_entero(m)} = {formato_entero(resto)}"),
            ("Normalización", f"{formato_entero(resto)} / {formato_entero(m)} = {formato_u(u, dec)}"),
        ]
        pasos.append(Paso(indice, subindice(indice), resto, u, formula, detalle))
        estados.append(resto)
        x = resto

    periodo, inicio = _detectar_periodo(estados)
    if inicio is not None:
        _aviso_ciclo(advertencias, periodo, inicio, subindice(inicio))
    if completo and periodo is None:
        advertencias.append(
            f"Se cumplen Hull–Dobell: el periodo completo es m = {formato_entero(m)}; "
            f"no se repite dentro de los primeros {n} valores."
        )
    return _base(
        "congruencial_lineal", p, [x0], pasos, advertencias, periodo, inicio, completo, m
    )


def _congruencial_multiplicativo(
    p: dict[str, int], n: int, dec: int, advertencias: list[str]
) -> Resultado:
    a, m, x0 = p["a"], p["m"], p["x0"]
    _validar_rango(m, "Módulo m", 2, 2_147_483_647, "m")
    _validar_rango(x0, "Semilla x₀", 1, m - 1, "x0")
    if mcd(x0, m) != 1:
        raise ErrorGeneracion(
            "La semilla x₀ debe ser coprima con m para no caer en un ciclo corto.",
            "x0",
        )

    primo = es_primo(m)
    primitiva = primo and es_raiz_primitiva(a, m)
    if not primo:
        advertencias.append(
            "m no es primo: el periodo máximo m − 1 no está garantizado. "
            "Para el generador de Lehmer se recomienda un módulo primo."
        )
    elif not primitiva:
        advertencias.append(
            "a no es raíz primitiva de m: el periodo será un divisor de m − 1, "
            "no necesariamente el máximo."
        )

    x = x0
    pasos: list[Paso] = []
    estados: list[int] = []
    for indice in range(1, n + 1):
        producto = a * x
        cociente, resto = divmod(producto, m)
        u = resto / m
        formula = (
            f"{subindice(indice)} = ({formato_entero(a)}·{subindice(indice - 1)})"
            f" mod {formato_entero(m)}"
        )
        detalle = [
            ("Producto", f"{formato_entero(a)} · {formato_entero(x)} = {formato_entero(producto)}"),
            ("División entera", f"{formato_entero(producto)} ÷ {formato_entero(m)} = {formato_entero(cociente)}"),
            ("Resto", f"{formato_entero(producto)} − {formato_entero(cociente)} · {formato_entero(m)} = {formato_entero(resto)}"),
            ("Normalización", f"{formato_entero(resto)} / {formato_entero(m)} = {formato_u(u, dec)}"),
        ]
        pasos.append(Paso(indice, subindice(indice), resto, u, formula, detalle))
        estados.append(resto)
        x = resto

    periodo, inicio = _detectar_periodo(estados)
    if inicio is not None:
        _aviso_ciclo(advertencias, periodo, inicio, subindice(inicio))
    if primitiva and periodo is None:
        advertencias.append(
            f"m es primo y a es raíz primitiva: el periodo máximo es "
            f"m − 1 = {formato_entero(m - 1)}."
        )
    return _base(
        "congruencial_multiplicativo",
        p,
        [x0],
        pasos,
        advertencias,
        periodo,
        inicio,
        primitiva,
        m,
    )


def _congruencial_aditivo(
    p: dict[str, int], n: int, dec: int, advertencias: list[str]
) -> Resultado:
    m, x0, x1 = p["m"], p["x0"], p["x1"]
    _validar_rango(m, "Módulo m", 2, 1_000_000_000, "m")
    _validar_semilla(x0, m)
    _validar_semilla(x1, m, "Semilla x₁")
    if x0 == 0 and x1 == 0:
        raise ErrorGeneracion(
            "Las dos semillas no pueden ser 0: la sucesión quedaría fija en 0.",
            "x1",
        )

    x_anterior, x_actual = x0, x1
    pasos: list[Paso] = []
    estados: list[tuple[int, int]] = []
    for indice in range(1, n + 1):
        suma = x_anterior + x_actual
        cociente, resto = divmod(suma, m)
        u = resto / m
        formula = (
            f"{subindice(indice + 1)} = ({subindice(indice - 1)} + "
            f"{subindice(indice)}) mod {formato_entero(m)}"
        )
        detalle = [
            ("Suma", f"{formato_entero(x_anterior)} + {formato_entero(x_actual)} = {formato_entero(suma)}"),
            ("División entera", f"{formato_entero(suma)} ÷ {formato_entero(m)} = {formato_entero(cociente)}"),
            ("Resto", f"{formato_entero(suma)} − {formato_entero(cociente)} · {formato_entero(m)} = {formato_entero(resto)}"),
            ("Normalización", f"{formato_entero(resto)} / {formato_entero(m)} = {formato_u(u, dec)}"),
        ]
        pasos.append(
            Paso(indice, subindice(indice + 1), resto, u, formula, detalle)
        )
        estados.append((x_anterior, x_actual))
        x_anterior, x_actual = x_actual, resto

    periodo, inicio = _detectar_periodo(estados)
    if inicio is not None:
        _aviso_ciclo(advertencias, periodo, inicio, subindice(inicio + 1))
    return _base(
        "congruencial_aditivo",
        p,
        [x0, x1],
        pasos,
        advertencias,
        periodo,
        inicio,
        False,
        m,
    )


def _congruencial_cuadratico(
    p: dict[str, int], n: int, dec: int, advertencias: list[str]
) -> Resultado:
    a, b, c, m, x0 = p["a"], p["b"], p["c"], p["m"], p["x0"]
    _validar_rango(m, "Módulo m", 2, 1_000_000_000, "m")
    _validar_semilla(x0, m)

    x = x0
    pasos: list[Paso] = []
    estados: list[int] = []
    for indice in range(1, n + 1):
        cuadrado = x * x
        termino_a = a * cuadrado
        termino_b = b * x
        total = termino_a + termino_b + c
        cociente, resto = divmod(total, m)
        u = resto / m
        formula = (
            f"{subindice(indice)} = ({formato_entero(a)}·{subindice(indice - 1)}²"
            f" + {formato_entero(b)}·{subindice(indice - 1)} + {formato_entero(c)})"
            f" mod {formato_entero(m)}"
        )
        detalle = [
            ("Cuadrado", f"{formato_entero(x)}² = {formato_entero(cuadrado)}"),
            ("Término a·x²", f"{formato_entero(a)} · {formato_entero(cuadrado)} = {formato_entero(termino_a)}"),
            ("Término b·x", f"{formato_entero(b)} · {formato_entero(x)} = {formato_entero(termino_b)}"),
            ("Suma total", f"{formato_entero(termino_a)} + {formato_entero(termino_b)} + {formato_entero(c)} = {formato_entero(total)}"),
            ("División entera", f"{formato_entero(total)} ÷ {formato_entero(m)} = {formato_entero(cociente)}"),
            ("Resto", f"{formato_entero(total)} − {formato_entero(cociente)} · {formato_entero(m)} = {formato_entero(resto)}"),
            ("Normalización", f"{formato_entero(resto)} / {formato_entero(m)} = {formato_u(u, dec)}"),
        ]
        pasos.append(Paso(indice, subindice(indice), resto, u, formula, detalle))
        estados.append(resto)
        x = resto

    periodo, inicio = _detectar_periodo(estados)
    if inicio is not None:
        _aviso_ciclo(advertencias, periodo, inicio, subindice(inicio))
    return _base(
        "congruencial_cuadratico",
        p,
        [x0],
        pasos,
        advertencias,
        periodo,
        inicio,
        False,
        m,
    )


# ---------------------------------------------------------------------------
# Estadísticas descriptivas y series para gráficas
# ---------------------------------------------------------------------------


def calcular_estadisticas(resultado: Resultado) -> Estadisticas:
    valores = resultado.valores_u
    n = len(valores)
    if n == 0:
        return Estadisticas(0.0, 0.0, 0.0, 0.0, 0.0)
    media = sum(valores) / n
    varianza = sum((valor - media) ** 2 for valor in valores) / n
    desviacion = varianza ** 0.5
    return Estadisticas(media, varianza, desviacion, min(valores), max(valores))


def histograma(resultado: Resultado, bins: int = 10) -> list[int]:
    conteos = [0] * bins
    for valor in resultado.valores_u:
        indice = int(valor * bins)
        if indice >= bins:
            indice = bins - 1
        conteos[indice] += 1
    return conteos


def texto_periodo(resultado: Resultado) -> tuple[str, str]:
    """Devuelve el valor y el subtítulo para la tarjeta de periodo."""
    if resultado.periodo is not None:
        inicio = resultado.inicio_periodo or 1
        return (
            f"{resultado.periodo}",
            f"ciclo desde {notacion_de_paso(resultado, inicio)}",
        )
    if resultado.periodo_teorico is None:
        return "—", "sin cota calculada"
    if resultado.periodo_exacto:
        return (
            formato_entero(resultado.periodo_teorico),
            f"teórico · {resultado.cantidad} pasos",
        )
    return (
        f"≤ {formato_entero(resultado.periodo_teorico)}",
        f"cota · {resultado.cantidad} pasos",
    )


def resumen_parametros(resultado: Resultado) -> str:
    """Texto compacto con los parámetros usados, para encabezados y exportación."""
    partes = []
    for campo in resultado.metodo.campos:
        if campo.clave in resultado.parametros:
            partes.append(f"{campo.clave} = {formato_entero(resultado.parametros[campo.clave])}")
    return " · ".join(partes)
