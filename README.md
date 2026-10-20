# AleatoriaLab

Calculadora educativa de números pseudoaleatorios hecha con **Python + Tkinter**.
Genera secuencias con siete métodos clásicos, muestra **el cálculo completo de cada número** y permite comparar la distribución con una uniforme \(U(0,1)\).

La lógica de generación está implementada con aritmética entera propia. **No se usa `random`, `numpy`, `scipy` ni otra librería para calcular los números.**

---

## Cómo ejecutar

Requisitos: Python 3.10 o superior (Tkinter viene incluido en la instalación oficial de Windows).

```bat
python main.py
```

También se puede hacer doble clic en **`ejecutar.bat`**, que busca `py` o `python` y abre la aplicación.

Pruebas del motor:

```bat
python -m unittest discover -s tests -v
```

---

## Qué incluye

- Menú lateral para cambiar de método sin perder los parámetros de los demás.
- Formulario dinámico con validaciones y mensajes de error en español.
- Resultado con media, varianza, desviación, rango, periodo detectado y avisos.
- Pestaña **Paso a paso**: cada número muestra su fórmula, operaciones intermedias, el resto de la división y la normalización \(U_n\).
- Pestaña **Tabla**: secuencia completa con resaltado del ciclo, copia al portapapeles y exportación CSV.
- Pestaña **Gráficas**: histograma de 10 intervalos y secuencia frente al paso, dibujados en un `Canvas`.
- Pestaña **El método**: idea, algoritmo, condiciones, fuente y periodo de la ejecución.
- Botón «Cargar ejemplo» con parámetros didácticos.
- Guía rápida (`F1`), atajos `Ctrl+Enter` para generar y `Ctrl+S` para exportar.

No hay dependencias externas: solo la biblioteca estándar de Python.

---

## Métodos implementados

| # | Método | Recurrencia | Normalización |
|---|--------|-------------|---------------|
| 01 | Cuadrados medios | \(x_n = \text{centro}_d(x_{n-1}^2)\) | \(U_n = x_n / 10^d\) |
| 02 | Productos medios | \(x_n = \text{centro}_d(x_{n-2} \cdot x_{n-1})\) | \(U_n = x_n / 10^d\) |
| 03 | Constante aditiva | \(x_n = (x_{n-1} + c) \bmod m\) | \(U_n = x_n / m\) |
| 04 | Congruencial lineal (mixto) | \(x_n = (a x_{n-1} + c) \bmod m\) | \(U_n = x_n / m\) |
| 05 | Congruencial multiplicativo | \(x_n = (a x_{n-1}) \bmod m\) | \(U_n = x_n / m\) |
| 06 | Congruencial aditivo | \(x_n = (x_{n-1} + x_{n-2}) \bmod m\) | \(U_n = x_n / m\) |
| 07 | Congruencial cuadrático | \(x_n = (a x_{n-1}^2 + b x_{n-1} + c) \bmod m\) | \(U_n = x_n / m\) |

El motor también comprueba:

- condiciones de **Hull–Dobell** para periodo completo del congruencial lineal;
- si el módulo es primo y el multiplicador es **raíz primitiva** en el congruencial multiplicativo;
- si \(c\) y \(m\) son coprimos en la constante aditiva;
- ciclos y puntos fijos en las secuencias generadas;
- rangos de semillas, módulos y cantidades.

---

## Estructura

```text
.
├── main.py                 # punto de entrada
├── interfaz.py             # ventana, menú, pestañas, gráficas y guía
├── generadores.py          # catálogo de métodos + motor + validaciones
├── ejecutar.bat            # lanzador para Windows
├── tests/
│   └── test_generadores.py # pruebas con secuencias conocidas
└── README.md
```

La separación es intencional: `generadores.py` no importa Tkinter y puede probarse por separado. La interfaz solo recoge datos, llama a `generar()` y presenta el `Resultado`.

---

## Por qué el paso a paso es confiable

Cada método construye sus propios objetos `Paso` con:

1. la notación del estado (`x₁`, `x₂`, …);
2. la fórmula aplicada;
3. el cuadrado, producto o suma intermedia;
4. la división entera y el resto;
5. la normalización a \([0,1)\);
6. una nota cuando hay cero, ciclo o degeneración.

Las pruebas incluyen secuencias calculadas a mano para todos los métodos y casos de validación (semillas fuera de rango, módulos inválidos, semilla no coprima, cantidades no permitidas).

---

## Referencias de apoyo

Material de estudio que acompañó el diseño de la aplicación:

- Raúl Coss Bu, *Simulación* — capítulo 2, generación de números aleatorios.
- Sheldon M. Ross, *Simulación*, 2.ª ed. — capítulo 3, números aleatorios.
- Agustín Jiménez Avello et al., *Simulación de procesos y aplicaciones*.
- Eduardo García Dunna et al., *Simulación y análisis de sistemas con ProModel*.
- *Simulation and Modeling to Understand the Change* (2021 y 2022).
- *Técnicas de Simulación y Remuestreo con R*.

La aplicación es material didáctico independiente. Los generadores clásicos incluidos no son adecuados para criptografía ni para producción; su valor está en entender cómo se construye y se evalúa una secuencia pseudoaleatoria.
