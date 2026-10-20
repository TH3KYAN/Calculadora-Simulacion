"""Interfaz Tkinter de AleatoriaLab.

La interfaz no calcula números: solo recoge parámetros, llama al motor
``generadores`` y presenta los resultados. No usa paquetes externos.
"""

from __future__ import annotations

import csv
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from generadores import (
    METODOS,
    ErrorGeneracion,
    Estadisticas,
    Metodo,
    Paso,
    Resultado,
    calcular_estadisticas,
    formato_entero,
    formato_u,
    generar,
    histograma,
    notacion_de_paso,
    resumen_parametros,
    texto_periodo,
)


# ---------------------------------------------------------------------------
# Paleta y tipografías
# ---------------------------------------------------------------------------

BG = "#f3f6fb"
WHITE = "#ffffff"
SIDEBAR = "#0b1424"
SIDEBAR_HOVER = "#121f34"
SIDEBAR_SEL = "#172842"
NAVY = "#111c2f"
TEXT = "#172033"
MUTED = "#64748b"
MUTED_2 = "#94a3b8"
LINE = "#e2e8f0"
LINE_SOFT = "#edf1f7"
PANEL = "#f8fafc"
ACCENT = "#0d9488"
ACCENT_DARK = "#0f766e"
ACCENT_SOFT = "#e6f7f4"
ACCENT_LINE = "#b7e8e1"
AMBER = "#b45309"
AMBER_SOFT = "#fffbeb"
AMBER_LINE = "#fde68a"
RED = "#b91c1c"
RED_SOFT = "#fef2f2"
RED_LINE = "#fecaca"
BLUE = "#2563eb"
BLUE_SOFT = "#eff6ff"


def _elegir_fuente(familias: set[str], candidatas: tuple[str, ...], respaldo: str) -> str:
    for nombre in candidatas:
        if nombre in familias:
            return nombre
    return respaldo


def _descendientes(widget: tk.Misc):
    for hijo in widget.winfo_children():
        yield hijo
        yield from _descendientes(hijo)


# ---------------------------------------------------------------------------
# Componentes reutilizables
# ---------------------------------------------------------------------------


class Boton(tk.Button):
    """Botón plano con estados de color consistentes en Windows."""

    VARIANTES = {
        "primary": (ACCENT, "#ffffff", ACCENT_DARK, "#0b5f59"),
        "secondary": ("#e8eef7", TEXT, "#d8e3f1", "#cbd8e9"),
        "ghost": (WHITE, MUTED, "#f1f5f9", "#e8eef5"),
        "ghost_dark": (SIDEBAR, "#cbd5e1", SIDEBAR_HOVER, "#1c2b44"),
        "soft": (ACCENT_SOFT, ACCENT_DARK, "#d5f1eb", "#c7ece5"),
        "danger_soft": (RED_SOFT, RED, "#fee2e2", "#fecaca"),
    }

    def __init__(
        self,
        master: tk.Misc,
        texto: str,
        comando: Optional[Callable[[], None]] = None,
        variante: str = "primary",
        fuente: Optional[tuple] = None,
        padx: int = 15,
        pady: int = 9,
        ancho: Optional[int] = None,
        **kwargs,
    ) -> None:
        base, fg, hover, pressed = self.VARIANTES.get(variante, self.VARIANTES["primary"])
        super().__init__(
            master,
            text=texto,
            command=comando,
            bg=base,
            fg=fg,
            activebackground=pressed if variante != "primary" else ACCENT_DARK,
            activeforeground=fg,
            disabledforeground=MUTED_2,
            relief="flat",
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            font=fuente or ("Segoe UI", 10, "bold"),
            padx=padx,
            pady=pady,
            width=ancho or 0,
            **kwargs,
        )
        self._base = base
        self._hover = hover
        self._fg = fg
        self.bind("<Enter>", self._entrar)
        self.bind("<Leave>", self._salir)

    def _entrar(self, _event=None) -> None:
        if str(self["state"]) != "disabled":
            self.configure(bg=self._hover)

    def _salir(self, _event=None) -> None:
        if str(self["state"]) != "disabled":
            self.configure(bg=self._base)

    def habilitar(self, activo: bool) -> None:
        self.configure(state="normal" if activo else "disabled")


class BotonMetodo(tk.Frame):
    """Fila seleccionable del menú lateral."""

    def __init__(
        self,
        master: tk.Misc,
        numero: str,
        metodo: Metodo,
        comando: Callable[[str], None],
        fuente_ui: str,
    ) -> None:
        super().__init__(master, bg=SIDEBAR, height=54, cursor="hand2")
        self.pack_propagate(False)
        self.metodo = metodo
        self._comando = comando
        self._fuente = fuente_ui
        self._seleccionado = False

        self.barra = tk.Frame(self, bg=SIDEBAR, width=3)
        self.barra.pack(side="left", fill="y")

        self.numero = tk.Label(
            self,
            text=numero,
            bg=SIDEBAR,
            fg="#5f7694",
            font=(fuente_ui, 8, "bold"),
            width=3,
            anchor="center",
        )
        self.numero.pack(side="left", fill="y", padx=(7, 2))

        textos = tk.Frame(self, bg=SIDEBAR)
        textos.pack(side="left", fill="both", expand=True, pady=8)

        self.nombre = tk.Label(
            textos,
            text=metodo.nombre,
            bg=SIDEBAR,
            fg="#dbe6f3",
            font=(fuente_ui, 10, "bold"),
            anchor="w",
        )
        self.nombre.pack(fill="x")

        self.resumen = tk.Label(
            textos,
            text=metodo.resumen,
            bg=SIDEBAR,
            fg="#7188a3",
            font=(fuente_ui, 8),
            anchor="w",
        )
        self.resumen.pack(fill="x")

        for widget in (self, self.barra, self.numero, textos, self.nombre, self.resumen):
            widget.bind("<Button-1>", self._click)
            widget.bind("<Enter>", self._entrar)
            widget.bind("<Leave>", self._salir)

    def _click(self, _event=None) -> None:
        self._comando(self.metodo.id)

    def _colores(self) -> tuple[str, str, str, str]:
        if self._seleccionado:
            return SIDEBAR_SEL, "#ffffff", "#8fe3d8", "#a9b8ca"
        return SIDEBAR, "#dbe6f3", "#5f7694", "#7188a3"

    def _aplicar(self, fondo: str) -> None:
        self.configure(bg=fondo)
        self.barra.configure(bg=ACCENT if self._seleccionado else fondo)
        self.numero.configure(bg=fondo)
        self.nombre.configure(bg=fondo)
        self.resumen.configure(bg=fondo)
        for hijo in self.winfo_children():
            if isinstance(hijo, tk.Frame) and hijo is not self.barra:
                hijo.configure(bg=fondo)

    def _entrar(self, _event=None) -> None:
        if not self._seleccionado:
            self._aplicar(SIDEBAR_HOVER)

    def _salir(self, _event=None) -> None:
        self._aplicar(SIDEBAR_SEL if self._seleccionado else SIDEBAR)

    def seleccionar(self, activo: bool) -> None:
        self._seleccionado = activo
        fondo, color_nombre, color_numero, color_resumen = self._colores()
        self._aplicar(fondo)
        self.nombre.configure(fg=color_nombre)
        self.numero.configure(fg=color_numero)
        self.resumen.configure(fg=color_resumen)
        self.barra.configure(bg=ACCENT if activo else fondo)
        self.nombre.configure(font=(self._fuente, 10, "bold" if activo else "normal"))


class TarjetaEstadistica(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        titulo: str,
        fuente_ui: str,
        fuente_mono: str,
        compacta: bool = False,
    ):
        super().__init__(
            master,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=LINE,
            bd=0,
        )
        self._fuente_mono = fuente_mono
        self._compacta = compacta
        tk.Label(
            self,
            text=titulo.upper(),
            bg=PANEL,
            fg=MUTED,
            font=(fuente_ui, 7 if compacta else 8, "bold"),
            anchor="w",
        ).pack(fill="x", padx=10 if compacta else 12, pady=(7 if compacta else 10, 1))
        self.valor = tk.Label(
            self,
            text="—",
            bg=PANEL,
            fg=NAVY,
            font=(fuente_mono, 15 if compacta else 17, "bold"),
            anchor="w",
        )
        self.valor.pack(fill="x", padx=10 if compacta else 12)
        self.detalle = tk.Label(
            self,
            text="",
            bg=PANEL,
            fg=MUTED_2,
            font=(fuente_ui, 7 if compacta else 8),
            anchor="w",
            justify="left",
            wraplength=110 if compacta else 130,
        )
        self.detalle.pack(fill="x", padx=10 if compacta else 12, pady=(0, 6 if compacta else 9))

    def actualizar(self, valor: str, detalle: str = "", tamano: int = 17) -> None:
        if self._compacta:
            tamano = min(tamano, 15)
        self.valor.configure(text=valor, font=(self._fuente_mono, tamano, "bold"))
        self.detalle.configure(text=detalle)


class MarcoDesplazable(tk.Frame):
    """Área vertical desplazable con rueda del ratón."""

    def __init__(self, master: tk.Misc, fondo: str = WHITE):
        super().__init__(master, bg=fondo)
        self.fondo = fondo
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            self,
            bg=fondo,
            highlightthickness=0,
            bd=0,
            yscrollincrement=24,
        )
        self.scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid(row=0, column=1, sticky="ns")
        self._scroll_visible = True

        self.interior = tk.Frame(self.canvas, bg=fondo)
        self.ventana = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.interior.bind("<Configure>", self._al_cambiar_interior)
        self.canvas.bind("<Configure>", self._al_cambiar_canvas)
        self.bind("<Enter>", self._activar_rueda)
        self.bind("<Leave>", self._desactivar_rueda)

    def _al_cambiar_interior(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.after_idle(self._actualizar_scrollbar)

    def _al_cambiar_canvas(self, event) -> None:
        self.canvas.itemconfigure(self.ventana, width=event.width)
        self.after_idle(self._actualizar_scrollbar)

    def _actualizar_scrollbar(self) -> None:
        if not self.canvas.winfo_exists():
            return
        necesario = self.interior.winfo_reqheight() > self.canvas.winfo_height() + 1
        if necesario and not self._scroll_visible:
            self.scroll.grid()
            self._scroll_visible = True
        elif not necesario and self._scroll_visible:
            self.scroll.grid_remove()
            self._scroll_visible = False

    def _activar_rueda(self, _event=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._rueda)
        self.canvas.bind_all("<Button-4>", self._rueda)
        self.canvas.bind_all("<Button-5>", self._rueda)

    def _desactivar_rueda(self, _event=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _rueda(self, event) -> None:
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -int(event.delta / 120) if event.delta else 0
        if delta:
            self.canvas.yview_scroll(delta, "units")

    def ir_al_inicio(self) -> None:
        self.canvas.yview_moveto(0)


# ---------------------------------------------------------------------------
# Gráficas dibujadas con Canvas
# ---------------------------------------------------------------------------


class GraficaBase(tk.Canvas):
    def __init__(self, master: tk.Misc, fuente_ui: str, alto: int = 220):
        super().__init__(
            master,
            bg=WHITE,
            highlightthickness=0,
            bd=0,
            height=alto,
        )
        self.fuente_ui = fuente_ui
        self._datos: Optional[Resultado] = None
        self._pendiente: Optional[str] = None
        self.bind("<Configure>", self._programar)

    def establecer_datos(self, resultado: Resultado) -> None:
        self._datos = resultado
        self._programar()

    def _programar(self, _event=None) -> None:
        if not self.winfo_exists():
            return
        if self._pendiente is not None:
            try:
                self.after_cancel(self._pendiente)
            except Exception:
                pass
        self._pendiente = self.after(40, self._dibujar)

    def _dibujar(self) -> None:
        self._pendiente = None
        if not self.winfo_exists():
            return
        self.delete("all")
        if self._datos is None:
            return
        ancho = self.winfo_width()
        alto = self.winfo_height()
        if ancho < 30 or alto < 30:
            return
        self.dibujar(self._datos, ancho, alto)

    def dibujar(self, resultado: Resultado, ancho: int, alto: int) -> None:
        raise NotImplementedError


class GraficaHistograma(GraficaBase):
    def dibujar(self, resultado: Resultado, ancho: int, alto: int) -> None:
        conteos = histograma(resultado, 10)
        maximo = max(conteos) if conteos else 1
        maximo = max(maximo, 1)
        izq, der, arriba, abajo = 42, 16, 20, 32
        area_ancho = max(1, ancho - izq - der)
        area_alto = max(1, alto - arriba - abajo)

        # Rejilla horizontal y etiquetas del eje Y.
        for i in range(5):
            y = arriba + area_alto * i / 4
            self.create_line(izq, y, ancho - der, y, fill="#eef2f7")
            valor = round(maximo * (4 - i) / 4)
            self.create_text(
                izq - 8,
                y,
                text=str(valor),
                anchor="e",
                fill=MUTED_2,
                font=(self.fuente_ui, 8),
            )

        # Barras.
        espacio = area_ancho / len(conteos)
        ancho_barra = max(6, espacio * 0.58)
        for i, conteo in enumerate(conteos):
            x_centro = izq + espacio * (i + 0.5)
            alto_barra = area_alto * conteo / maximo
            y0 = arriba + area_alto - alto_barra
            y1 = arriba + area_alto
            self.create_rectangle(
                x_centro - ancho_barra / 2,
                y0,
                x_centro + ancho_barra / 2,
                y1,
                fill=ACCENT if i % 2 == 0 else "#2bb3a4",
                outline="",
            )
            if conteo:
                self.create_text(
                    x_centro,
                    max(arriba + 7, y0 - 7),
                    text=str(conteo),
                    fill=ACCENT_DARK,
                    font=(self.fuente_ui, 8, "bold"),
                )

        # Línea esperada para una uniforme.
        esperado = len(resultado.pasos) / len(conteos)
        if maximo:
            y_esperado = arriba + area_alto - area_alto * esperado / maximo
            self.create_line(
                izq,
                y_esperado,
                ancho - der,
                y_esperado,
                fill=AMBER,
                dash=(5, 4),
                width=1,
            )

        # Eje X.
        self.create_line(izq, arriba + area_alto, ancho - der, arriba + area_alto, fill="#cbd5e1")
        for i in range(0, 11, 2):
            x = izq + area_ancho * i / 10
            self.create_line(x, arriba + area_alto, x, arriba + area_alto + 4, fill="#cbd5e1")
            self.create_text(
                x,
                alto - 12,
                text=f"{i / 10:.1f}".replace(".", ","),
                fill=MUTED,
                font=(self.fuente_ui, 8),
            )
        self.create_text(
            izq,
            8,
            text="frecuencia",
            anchor="w",
            fill=MUTED_2,
            font=(self.fuente_ui, 8),
        )


class GraficaSecuencia(GraficaBase):
    def dibujar(self, resultado: Resultado, ancho: int, alto: int) -> None:
        izq, der, arriba, abajo = 42, 18, 18, 30
        area_ancho = max(1, ancho - izq - der)
        area_alto = max(1, alto - arriba - abajo)
        valores = resultado.valores_u
        n = len(valores)

        for i in range(5):
            y = arriba + area_alto * i / 4
            self.create_line(izq, y, ancho - der, y, fill="#eef2f7")
            valor = 1 - i / 4
            self.create_text(
                izq - 8,
                y,
                text=f"{valor:.2f}".replace(".", ","),
                anchor="e",
                fill=MUTED_2,
                font=(self.fuente_ui, 8),
            )

        if n == 1:
            x = izq + area_ancho / 2
            y = arriba + area_alto * (1 - valores[0])
            self.create_oval(x - 4, y - 4, x + 4, y + 4, fill=ACCENT, outline="")
        else:
            puntos = []
            for i, valor in enumerate(valores):
                x = izq + area_ancho * i / (n - 1)
                y = arriba + area_alto * (1 - valor)
                puntos.extend([x, y])
            self.create_line(*puntos, fill=ACCENT, width=2, smooth=False)
            for i, valor in enumerate(valores):
                x = izq + area_ancho * i / (n - 1)
                y = arriba + area_alto * (1 - valor)
                self.create_oval(
                    x - 2.5,
                    y - 2.5,
                    x + 2.5,
                    y + 2.5,
                    fill=WHITE,
                    outline=ACCENT,
                    width=1,
                )

        # Media observada.
        media = sum(valores) / n if n else 0
        y_media = arriba + area_alto * (1 - media)
        self.create_line(izq, y_media, ancho - der, y_media, fill=AMBER, dash=(5, 4))
        self.create_text(
            ancho - der,
            max(arriba + 7, y_media - 9),
            text=f"media {formato_u(media, 3)}",
            anchor="e",
            fill=AMBER,
            font=(self.fuente_ui, 8),
        )

        self.create_line(izq, arriba + area_alto, ancho - der, arriba + area_alto, fill="#cbd5e1")
        self.create_text(
            izq,
            alto - 10,
            text="1",
            anchor="w",
            fill=MUTED_2,
            font=(self.fuente_ui, 8),
        )
        self.create_text(
            izq + area_ancho / 2,
            alto - 10,
            text=f"n = {n}",
            fill=MUTED_2,
            font=(self.fuente_ui, 8),
        )
        self.create_text(
            ancho - der,
            alto - 10,
            text=f"{n}",
            anchor="e",
            fill=MUTED_2,
            font=(self.fuente_ui, 8),
        )


# ---------------------------------------------------------------------------
# Aplicación
# ---------------------------------------------------------------------------


class Aplicacion(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AleatoriaLab · Calculadora de números pseudoaleatorios")
        self.configure(bg=BG)
        self.update_idletasks()
        ancho_inicial = min(1440, max(1240, self.winfo_screenwidth() - 80))
        alto_inicial = min(900, max(700, self.winfo_screenheight() - 100))
        self.geometry(f"{ancho_inicial}x{alto_inicial}")
        self.minsize(1240, 700)
        self._centrar(ancho_inicial, alto_inicial)

        familias = set(tkfont.families(self))
        self.fuente_ui = _elegir_fuente(
            familias, ("Segoe UI", "Aptos", "Calibri", "Helvetica"), "TkDefaultFont"
        )
        self.fuente_mono = _elegir_fuente(
            familias, ("Cascadia Mono", "Consolas", "Courier New"), "TkFixedFont"
        )
        self.option_add("*Font", (self.fuente_ui, 10))
        self._configurar_estilos()
        self._crear_icono()

        self.metodo_actual: Metodo = METODOS[0]
        self.resultado: Optional[Resultado] = None
        self.campos_vars: dict[str, tk.StringVar] = {}
        self.campos_entries: dict[str, ttk.Entry] = {}
        self.botones_metodo: dict[str, BotonMetodo] = {}
        self.valores_guardados: dict[str, dict[str, str]] = {}
        self.cantidad_var = tk.StringVar(value="12")
        self.decimales_var = tk.StringVar(value="6")
        self.error_var = tk.StringVar(value="")
        self._graficas: list[GraficaBase] = []
        self._notebook: Optional[ttk.Notebook] = None
        self._tab_graficas: Optional[tk.Frame] = None
        self._tab_metodo: Optional[tk.Frame] = None
        self._pasos_marco: Optional[MarcoDesplazable] = None

        self._construir_layout()
        self.seleccionar_metodo(self.metodo_actual.id, inicial=True)
        self.bind("<Control-Return>", lambda _e: self.generar())
        self.bind("<Control-s>", lambda _e: self.exportar_csv())
        self.bind("<F1>", lambda _e: self.abrir_guia())

    # -- infraestructura -----------------------------------------------------

    def _centrar(self, ancho: int, alto: int) -> None:
        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - ancho) // 2)
        y = max(0, (self.winfo_screenheight() - alto) // 2)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _configurar_estilos(self) -> None:
        estilo = ttk.Style(self)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass

        estilo.configure(".", background=BG, foreground=TEXT, font=(self.fuente_ui, 10))
        estilo.configure("TFrame", background=BG)
        estilo.configure("Card.TFrame", background=WHITE)
        estilo.configure("Panel.TFrame", background=PANEL)
        estilo.configure("TLabel", background=BG, foreground=TEXT)
        estilo.configure("Muted.TLabel", background=BG, foreground=MUTED)

        estilo.configure(
            "Campo.TEntry",
            fieldbackground=WHITE,
            foreground=TEXT,
            bordercolor=LINE,
            lightcolor=LINE,
            darkcolor=LINE,
            insertcolor=TEXT,
            padding=7,
        )
        estilo.map(
            "Campo.TEntry",
            bordercolor=[("focus", ACCENT)],
            lightcolor=[("focus", ACCENT)],
            darkcolor=[("focus", ACCENT)],
        )

        estilo.configure(
            "TNotebook",
            background=WHITE,
            borderwidth=0,
            tabmargins=(0, 6, 0, 0),
        )
        estilo.configure(
            "TNotebook.Tab",
            background=WHITE,
            foreground=MUTED,
            padding=(15, 9),
            font=(self.fuente_ui, 9, "bold"),
            borderwidth=0,
        )
        estilo.map(
            "TNotebook.Tab",
            background=[("selected", ACCENT_SOFT), ("active", "#f0fdfa")],
            foreground=[("selected", ACCENT_DARK), ("active", NAVY)],
            expand=[("selected", (0, 0, 0, 0))],
        )

        estilo.configure(
            "Treeview",
            background=WHITE,
            fieldbackground=WHITE,
            foreground=TEXT,
            rowheight=30,
            borderwidth=0,
            font=(self.fuente_mono, 10),
        )
        estilo.configure(
            "Treeview.Heading",
            background=PANEL,
            foreground=MUTED,
            relief="flat",
            font=(self.fuente_ui, 8, "bold"),
            padding=(8, 9),
        )
        estilo.map(
            "Treeview",
            background=[("selected", ACCENT_SOFT)],
            foreground=[("selected", NAVY)],
        )
        estilo.map(
            "Treeview.Heading",
            background=[("active", "#eef2f7")],
        )
        estilo.configure(
            "Vertical.TScrollbar",
            background="#cbd5e1",
            troughcolor=PANEL,
            bordercolor=PANEL,
            arrowcolor=MUTED,
            width=11,
        )
        estilo.configure(
            "Horizontal.TScrollbar",
            background="#cbd5e1",
            troughcolor=PANEL,
            bordercolor=PANEL,
            arrowcolor=MUTED,
            width=11,
        )
        estilo.configure("TSeparator", background=LINE)

    def _crear_icono(self) -> None:
        icono = tk.PhotoImage(width=32, height=32)
        icono.put(SIDEBAR, to=(0, 0, 32, 32))
        icono.put(ACCENT, to=(3, 3, 29, 29))
        icono.put("#14b8a6", to=(5, 5, 27, 27))
        for x, y in ((7, 7), (17, 7), (12, 13), (22, 13), (7, 19), (17, 19), (12, 25)):
            icono.put("#ffffff", to=(x, y, x + 4, y + 4))
        self._icono = icono
        try:
            self.iconphoto(True, icono)
        except tk.TclError:
            pass

    def _hacer_texto_ajustable(self, contenedor: tk.Misc, margen: int = 34, minimo: int = 260) -> None:
        """Ajusta el ancho de las etiquetas largas al ancho real del contenedor."""

        def aplicar(ancho: int) -> None:
            if not contenedor.winfo_exists():
                return
            ancho_util = max(minimo, ancho - margen)
            for widget in _descendientes(contenedor):
                if isinstance(widget, tk.Label) and len(str(widget.cget("text"))) > 40:
                    widget.configure(wraplength=ancho_util)

        contenedor.bind("<Configure>", lambda event: aplicar(event.width))

        def diferido() -> None:
            if contenedor.winfo_exists():
                aplicar(contenedor.winfo_width())

        self.after(40, diferido)

    # -- layout principal ----------------------------------------------------

    def _construir_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0, minsize=272)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._construir_sidebar()

        self.main = tk.Frame(self, bg=BG)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(2, weight=1)

        self._construir_topbar()
        self._construir_intro()

        self.cuerpo = tk.Frame(self.main, bg=BG)
        self.cuerpo.grid(row=2, column=0, sticky="nsew", padx=30, pady=(0, 22))
        self.cuerpo.grid_columnconfigure(0, minsize=356, weight=0)
        self.cuerpo.grid_columnconfigure(1, weight=1)
        self.cuerpo.grid_rowconfigure(0, weight=1)

        self.config_card = tk.Frame(
            self.cuerpo,
            bg=WHITE,
            highlightthickness=1,
            highlightbackground=LINE,
            bd=0,
        )
        self.config_card.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        self.results_card = tk.Frame(
            self.cuerpo,
            bg=WHITE,
            highlightthickness=1,
            highlightbackground=LINE,
            bd=0,
        )
        self.results_card.grid(row=0, column=1, sticky="nsew")
        self._construir_resultados()

    def _construir_sidebar(self) -> None:
        self.sidebar = tk.Frame(self, bg=SIDEBAR, width=272)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(2, weight=1)

        marca = tk.Frame(self.sidebar, bg=SIDEBAR)
        marca.grid(row=0, column=0, sticky="ew", padx=22, pady=(24, 18))
        marca.grid_columnconfigure(1, weight=1)

        logo = tk.Canvas(marca, width=42, height=42, bg=SIDEBAR, highlightthickness=0)
        logo.grid(row=0, column=0, rowspan=2, sticky="w")
        logo.create_rectangle(1, 1, 41, 41, fill="#0f2c3b", outline="")
        logo.create_rectangle(3, 3, 39, 39, fill=ACCENT, outline="")
        for x, y in ((8, 8), (22, 8), (15, 15), (29, 15), (8, 22), (22, 22), (15, 29)):
            logo.create_rectangle(x, y, x + 5, y + 5, fill="#ffffff", outline="")
        logo.create_text(
            31,
            31,
            text="₀₁",
            fill="#bff5ec",
            font=(self.fuente_mono, 7, "bold"),
            anchor="se",
        )

        tk.Label(
            marca,
            text="AleatoriaLab",
            bg=SIDEBAR,
            fg="#ffffff",
            font=(self.fuente_ui, 15, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", padx=(12, 0))

        tk.Label(
            marca,
            text="Simulación · U(0,1)",
            bg=SIDEBAR,
            fg="#7790aa",
            font=(self.fuente_ui, 8),
            anchor="w",
        ).grid(row=1, column=1, sticky="nw", padx=(12, 0), pady=(2, 0))

        metodos_cab = tk.Frame(self.sidebar, bg=SIDEBAR)
        metodos_cab.grid(row=1, column=0, sticky="ew", padx=22)
        tk.Label(
            metodos_cab,
            text="MÉTODOS",
            bg=SIDEBAR,
            fg="#5d7693",
            font=(self.fuente_ui, 8, "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            metodos_cab,
            text=f"{len(METODOS):02d}",
            bg="#13233a",
            fg="#8fb0c9",
            font=(self.fuente_mono, 8, "bold"),
            padx=6,
            pady=1,
        ).pack(side="right")

        self.metodos_marco = tk.Frame(self.sidebar, bg=SIDEBAR)
        self.metodos_marco.grid(row=2, column=0, sticky="new", padx=10, pady=(8, 0))

        categoria_actual = None
        for numero, metodo in enumerate(METODOS, 1):
            if metodo.categoria != categoria_actual:
                categoria_actual = metodo.categoria
                tk.Label(
                    self.metodos_marco,
                    text=categoria_actual,
                    bg=SIDEBAR,
                    fg="#49617d",
                    font=(self.fuente_ui, 7, "bold"),
                    anchor="w",
                ).pack(fill="x", padx=12, pady=(12, 5))
            boton = BotonMetodo(
                self.metodos_marco,
                f"{numero:02d}",
                metodo,
                self.seleccionar_metodo,
                self.fuente_ui,
            )
            boton.pack(fill="x", pady=1)
            self.botones_metodo[metodo.id] = boton

        pie = tk.Frame(self.sidebar, bg=SIDEBAR)
        pie.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 20))
        tk.Frame(pie, bg="#1b2b44", height=1).pack(fill="x", pady=(0, 14))
        tk.Label(
            pie,
            text="MOTOR PROPIO",
            bg=SIDEBAR,
            fg="#4d6a87",
            font=(self.fuente_ui, 7, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            pie,
            text="Aritmética entera · sin random()",
            bg=SIDEBAR,
            fg="#8ca2b8",
            font=(self.fuente_ui, 8),
            anchor="w",
        ).pack(fill="x", pady=(3, 0))
        tk.Label(
            pie,
            text="Python + Tkinter · 100 % local",
            bg=SIDEBAR,
            fg="#5d7693",
            font=(self.fuente_ui, 8),
            anchor="w",
        ).pack(fill="x", pady=(2, 10))

        Boton(
            pie,
            texto="Guía rápida  ·  F1",
            comando=self.abrir_guia,
            variante="ghost_dark",
            fuente=(self.fuente_ui, 8, "bold"),
            padx=10,
            pady=7,
            anchor="w",
        ).pack(fill="x")

    def _construir_topbar(self) -> None:
        barra = tk.Frame(self.main, bg=BG)
        barra.grid(row=0, column=0, sticky="ew", padx=30, pady=(18, 0))
        barra.grid_columnconfigure(0, weight=1)

        tk.Label(
            barra,
            text="LABORATORIO DE SIMULACIÓN",
            bg=BG,
            fg=MUTED_2,
            font=(self.fuente_ui, 8, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        acciones = tk.Frame(barra, bg=BG)
        acciones.grid(row=0, column=1, sticky="e")
        Boton(
            acciones,
            texto="¿Cómo funciona?",
            comando=self.abrir_guia,
            variante="ghost",
            fuente=(self.fuente_ui, 9, "bold"),
            padx=10,
            pady=5,
        ).pack(side="left", padx=(0, 6))
        chip = tk.Frame(acciones, bg="#ecfdf5", highlightthickness=1, highlightbackground="#bbf7d0")
        chip.pack(side="left")
        tk.Label(
            chip,
            text="●  100 % local",
            bg="#ecfdf5",
            fg="#047857",
            font=(self.fuente_ui, 8, "bold"),
            padx=9,
            pady=4,
        ).pack()

    def _construir_intro(self) -> None:
        intro = tk.Frame(self.main, bg=BG)
        intro.grid(row=1, column=0, sticky="ew", padx=30, pady=(14, 18))
        intro.grid_columnconfigure(0, weight=1)

        izquierda = tk.Frame(intro, bg=BG)
        izquierda.grid(row=0, column=0, sticky="nsew")
        self.eyebrow = tk.Label(
            izquierda,
            text="MÉTODO 01 · CLÁSICOS",
            bg=BG,
            fg=ACCENT_DARK,
            font=(self.fuente_ui, 8, "bold"),
            anchor="w",
        )
        self.eyebrow.pack(fill="x")
        self.titulo_metodo = tk.Label(
            izquierda,
            text="Cuadrados medios",
            bg=BG,
            fg=NAVY,
            font=(self.fuente_ui, 27, "bold"),
            anchor="w",
        )
        self.titulo_metodo.pack(fill="x", pady=(2, 1))
        self.descripcion_metodo = tk.Label(
            izquierda,
            text="",
            bg=BG,
            fg=MUTED,
            font=(self.fuente_ui, 10),
            anchor="w",
            justify="left",
            wraplength=560,
        )
        self.descripcion_metodo.pack(fill="x")

        def ajustar_intro(event) -> None:
            self.descripcion_metodo.configure(wraplength=max(320, event.width - 6))

        izquierda.bind("<Configure>", ajustar_intro)

        self.formula_card = tk.Frame(
            intro,
            bg=ACCENT_SOFT,
            highlightthickness=1,
            highlightbackground=ACCENT_LINE,
            bd=0,
        )
        self.formula_card.grid(row=0, column=1, sticky="e", padx=(22, 0))
        tk.Label(
            self.formula_card,
            text="FÓRMULA",
            bg=ACCENT_SOFT,
            fg=ACCENT_DARK,
            font=(self.fuente_ui, 7, "bold"),
            anchor="w",
        ).pack(fill="x", padx=15, pady=(10, 0))
        self.formula_label = tk.Label(
            self.formula_card,
            text="",
            bg=ACCENT_SOFT,
            fg="#0f5f59",
            font=(self.fuente_mono, 10, "bold"),
            anchor="w",
            justify="left",
            wraplength=360,
        )
        self.formula_label.pack(fill="x", padx=15, pady=(2, 11))

        def ajustar_formula(event) -> None:
            self.formula_label.configure(wraplength=max(280, event.width - 30))

        self.formula_card.bind("<Configure>", ajustar_formula)

    def _construir_resultados(self) -> None:
        cabecera = tk.Frame(self.results_card, bg=WHITE)
        cabecera.pack(fill="x", padx=18, pady=(14, 0))
        cabecera.grid_columnconfigure(0, weight=1)
        tk.Label(
            cabecera,
            text="Resultados",
            bg=WHITE,
            fg=NAVY,
            font=(self.fuente_ui, 12, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        self.resultado_sub = tk.Label(
            cabecera,
            text="Configura los parámetros y genera una secuencia.",
            bg=WHITE,
            fg=MUTED,
            font=(self.fuente_ui, 8),
            anchor="w",
        )
        self.resultado_sub.grid(row=1, column=0, sticky="w", pady=(2, 0))

        acciones = tk.Frame(cabecera, bg=WHITE)
        acciones.grid(row=0, column=1, rowspan=2, sticky="e")
        self.btn_copiar = Boton(
            acciones,
            texto="Copiar tabla",
            comando=self.copiar_tabla,
            variante="ghost",
            fuente=(self.fuente_ui, 8, "bold"),
            padx=9,
            pady=5,
        )
        self.btn_copiar.pack(side="left", padx=(0, 5))
        self.btn_exportar = Boton(
            acciones,
            texto="Exportar CSV",
            comando=self.exportar_csv,
            variante="secondary",
            fuente=(self.fuente_ui, 8, "bold"),
            padx=9,
            pady=5,
        )
        self.btn_exportar.pack(side="left")
        self._habilitar_acciones(False)

        tk.Frame(self.results_card, bg=LINE_SOFT, height=1).pack(fill="x", padx=18, pady=(12, 0))
        self.results_body = tk.Frame(self.results_card, bg=WHITE)
        self.results_body.pack(fill="both", expand=True, padx=18, pady=(12, 14))

        self._mostrar_vacio()

    # -- navegación y configuración -----------------------------------------

    def seleccionar_metodo(self, metodo_id: str, inicial: bool = False) -> None:
        if not inicial and metodo_id == self.metodo_actual.id:
            return
        if not inicial:
            self._guardar_valores_actuales()
        self.metodo_actual = next(m for m in METODOS if m.id == metodo_id)
        for clave, boton in self.botones_metodo.items():
            boton.seleccionar(clave == metodo_id)

        numero = METODOS.index(self.metodo_actual) + 1
        self.eyebrow.configure(
            text=f"MÉTODO {numero:02d} / {len(METODOS):02d} · {self.metodo_actual.categoria}"
        )
        self.titulo_metodo.configure(text=self.metodo_actual.nombre)
        self.descripcion_metodo.configure(text=self.metodo_actual.descripcion)
        self.formula_label.configure(text=self.metodo_actual.formula)
        self._construir_configuracion()
        self._mostrar_vacio()
        self.resultado = None
        self.resultado_sub.configure(text="Configura los parámetros y genera una secuencia.")
        self._habilitar_acciones(False)

    def _construir_configuracion(self) -> None:
        for hijo in self.config_card.winfo_children():
            hijo.destroy()
        self.campos_vars = {}
        self.campos_entries = {}
        self.error_var.set("")

        cabecera = tk.Frame(self.config_card, bg=WHITE)
        cabecera.pack(fill="x", padx=20, pady=(16, 0))
        tk.Label(
            cabecera,
            text="Configuración",
            bg=WHITE,
            fg=NAVY,
            font=(self.fuente_ui, 12, "bold"),
            anchor="w",
        ).pack(side="left")
        Boton(
            cabecera,
            texto="Cargar ejemplo",
            comando=self.cargar_ejemplo,
            variante="soft",
            fuente=(self.fuente_ui, 8, "bold"),
            padx=8,
            pady=4,
        ).pack(side="right")

        pie = tk.Frame(self.config_card, bg=WHITE)
        pie.pack(side="bottom", fill="x", padx=20, pady=(10, 16))

        self.error_frame = tk.Frame(
            pie,
            bg=RED_SOFT,
            highlightthickness=1,
            highlightbackground=RED_LINE,
        )
        self.error_label = tk.Label(
            self.error_frame,
            textvariable=self.error_var,
            bg=RED_SOFT,
            fg=RED,
            font=(self.fuente_ui, 8),
            justify="left",
            anchor="w",
            wraplength=290,
            padx=9,
            pady=7,
        )
        self.error_label.pack(fill="x")
        if self.error_var.get():
            self.error_frame.pack(fill="x", pady=(0, 8))
        else:
            self.error_frame.pack_forget()

        self.btn_generar = Boton(
            pie,
            texto="Generar secuencia  ·  Ctrl + ↵",
            comando=self.generar,
            variante="primary",
            fuente=(self.fuente_ui, 10, "bold"),
            pady=11,
        )
        self.btn_generar.pack(fill="x")

        secuencia = tk.Frame(self.config_card, bg=WHITE)
        secuencia.pack(side="bottom", fill="x", padx=20, pady=(8, 0))
        tk.Frame(secuencia, bg=LINE_SOFT, height=1).pack(fill="x", pady=(0, 9))
        tk.Label(
            secuencia,
            text="SECUENCIA",
            bg=WHITE,
            fg=MUTED_2,
            font=(self.fuente_ui, 7, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 5))
        comunes = tk.Frame(secuencia, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        comunes.pack(fill="x")
        comunes.grid_columnconfigure(0, weight=1)
        comunes.grid_columnconfigure(1, weight=1)
        self._campo_comun(comunes, 0, "Números", self.cantidad_var, "1 – 100")
        self._campo_comun(comunes, 1, "Decimales", self.decimales_var, "2 – 8")

        desplazable = MarcoDesplazable(self.config_card, WHITE)
        desplazable.pack(fill="both", expand=True, padx=(20, 9), pady=(8, 0))
        contenido = desplazable.interior

        tk.Label(
            contenido,
            text="PARÁMETROS DEL MÉTODO",
            bg=WHITE,
            fg=MUTED_2,
            font=(self.fuente_ui, 7, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(2, 8))

        guardados = self.valores_guardados.get(self.metodo_actual.id, {})
        for campo in self.metodo_actual.campos:
            fila = tk.Frame(contenido, bg=WHITE)
            fila.pack(fill="x", pady=(0, 7))
            superior = tk.Frame(fila, bg=WHITE)
            superior.pack(fill="x")
            tk.Label(
                superior,
                text=campo.etiqueta,
                bg=WHITE,
                fg=TEXT,
                font=(self.fuente_ui, 9, "bold"),
                anchor="w",
            ).pack(side="left")
            var = tk.StringVar(value=str(guardados.get(campo.clave, campo.defecto)))
            entrada = ttk.Entry(
                superior,
                textvariable=var,
                width=14,
                justify="right",
                style="Campo.TEntry",
                font=(self.fuente_mono, 10),
            )
            entrada.pack(side="right")
            tk.Label(
                fila,
                text=campo.ayuda,
                bg=WHITE,
                fg=MUTED_2,
                font=(self.fuente_ui, 8),
                anchor="w",
            ).pack(fill="x", pady=(1, 0))
            entrada.bind("<Return>", lambda _e: self.generar())
            self.campos_vars[campo.clave] = var
            self.campos_entries[campo.clave] = entrada

        self._configurar_atajo_digitos()

    def _campo_comun(
        self,
        master: tk.Misc,
        columna: int,
        titulo: str,
        var: tk.StringVar,
        rango: str,
    ) -> None:
        marco = tk.Frame(master, bg=PANEL)
        marco.grid(row=0, column=columna, sticky="ew", padx=10, pady=7)
        tk.Label(
            marco,
            text=titulo,
            bg=PANEL,
            fg=TEXT,
            font=(self.fuente_ui, 8, "bold"),
            anchor="w",
        ).pack(fill="x")
        fila = tk.Frame(marco, bg=PANEL)
        fila.pack(fill="x", pady=(2, 0))
        entrada = ttk.Entry(
            fila,
            textvariable=var,
            width=7,
            justify="right",
            style="Campo.TEntry",
            font=(self.fuente_mono, 10),
        )
        entrada.pack(side="left")
        tk.Label(
            fila,
            text=rango,
            bg=PANEL,
            fg=MUTED_2,
            font=(self.fuente_ui, 7),
        ).pack(side="left", padx=(6, 0))
        entrada.bind("<Return>", lambda _e: self.generar())

    def _configurar_atajo_digitos(self) -> None:
        if "d" not in self.campos_vars:
            return
        var_d = self.campos_vars["d"]

        def al_cambiar(*_args) -> None:
            try:
                d = int(var_d.get())
            except ValueError:
                return
            if d < 2:
                return
            limite = 10 ** d - 1
            for clave in ("x0", "x1"):
                if clave in self.campos_vars:
                    try:
                        actual = int(self.campos_vars[clave].get())
                    except ValueError:
                        continue
                    if actual > limite:
                        self.campos_vars[clave].set(str(limite))

        var_d.trace_add("write", al_cambiar)

    def _guardar_valores_actuales(self) -> None:
        if not self.campos_vars:
            return
        self.valores_guardados[self.metodo_actual.id] = {
            clave: var.get() for clave, var in self.campos_vars.items()
        }

    def cargar_ejemplo(self) -> None:
        for clave, valor in self.metodo_actual.ejemplo.items():
            if clave in self.campos_vars:
                self.campos_vars[clave].set(str(valor))
        self.cantidad_var.set("12")
        self.decimales_var.set("6")
        self._ocultar_error()
        self._guardar_valores_actuales()
        if self.resultado is not None:
            self.resultado = None
            self._mostrar_vacio()
            self._habilitar_acciones(False)
            self.resultado_sub.configure(
                text="Ejemplo cargado. Pulsa «Generar secuencia» para calcularlo."
            )

    # -- generación y presentación ------------------------------------------

    def _valores_formulario(self) -> dict[str, str]:
        return {clave: var.get() for clave, var in self.campos_vars.items()}

    def generar(self) -> None:
        self._ocultar_error()
        try:
            resultado = generar(
                self.metodo_actual.id,
                self._valores_formulario(),
                self.cantidad_var.get(),
                self.decimales_var.get(),
            )
        except ErrorGeneracion as error:
            self._mostrar_error(error.mensaje)
            if error.campo and error.campo in self.campos_entries:
                self.campos_entries[error.campo].focus_set()
            return
        except Exception as error:  # pragma: no cover - red de seguridad de la UI
            self._mostrar_error(f"No se pudo generar la secuencia: {error}")
            return

        self.resultado = resultado
        self._guardar_valores_actuales()
        self._presentar_resultado(resultado)

    def _mostrar_error(self, mensaje: str) -> None:
        self.error_var.set(mensaje)
        if hasattr(self, "error_frame"):
            self.error_frame.pack_forget()
            self.error_frame.pack(fill="x", pady=(0, 8), before=self.btn_generar)

    def _ocultar_error(self) -> None:
        self.error_var.set("")
        if hasattr(self, "error_frame"):
            self.error_frame.pack_forget()

    def _habilitar_acciones(self, activo: bool) -> None:
        self.btn_copiar.habilitar(activo)
        self.btn_exportar.habilitar(activo)

    def _limpiar_resultados(self) -> None:
        for hijo in self.results_body.winfo_children():
            hijo.destroy()
        self._graficas.clear()
        self._notebook = None
        self._tab_graficas = None
        self._tab_metodo = None
        self._pasos_marco = None

    def _mostrar_vacio(self) -> None:
        self._limpiar_resultados()
        vacio = tk.Frame(self.results_body, bg=WHITE)
        vacio.pack(fill="both", expand=True)

        lienzo = tk.Canvas(vacio, bg=WHITE, highlightthickness=0, height=190)
        lienzo.pack(fill="x", pady=(8, 4))

        def dibujar(_event=None) -> None:
            if not lienzo.winfo_exists():
                return
            lienzo.delete("all")
            ancho = lienzo.winfo_width()
            alto = lienzo.winfo_height()
            if ancho < 50:
                return
            centro = ancho / 2
            for x in range(0, int(ancho), 26):
                for y in range(14, alto - 8, 26):
                    if (x // 26 + y // 26) % 5 == 0:
                        lienzo.create_oval(x, y, x + 2, y + 2, fill="#dbe7f0", outline="")
            lienzo.create_text(
                centro,
                alto / 2 - 14,
                text="U(0,1)",
                fill="#c7e9e4",
                font=(self.fuente_mono, 39, "bold"),
            )
            lienzo.create_text(
                centro,
                alto / 2 + 28,
                text="todavía no hay una secuencia",
                fill=MUTED_2,
                font=(self.fuente_ui, 9),
            )

        lienzo.bind("<Configure>", dibujar)
        self.after(40, dibujar)

        tk.Label(
            vacio,
            text="Tu secuencia aparecerá aquí",
            bg=WHITE,
            fg=NAVY,
            font=(self.fuente_ui, 15, "bold"),
        ).pack(pady=(2, 4))
        tk.Label(
            vacio,
            text="Elige un método, ajusta sus parámetros y pulsa «Generar secuencia».\n"
            "Cada resultado incluye el cálculo completo, la tabla de valores y sus gráficas.",
            bg=WHITE,
            fg=MUTED,
            font=(self.fuente_ui, 9),
            justify="center",
        ).pack(pady=(0, 12))
        Boton(
            vacio,
            texto="Generar con el ejemplo",
            comando=self._generar_ejemplo,
            variante="soft",
            fuente=(self.fuente_ui, 9, "bold"),
            padx=14,
            pady=8,
        ).pack()

    def _generar_ejemplo(self) -> None:
        self.cargar_ejemplo()
        self.generar()

    def _presentar_resultado(self, resultado: Resultado) -> None:
        self._limpiar_resultados()
        self.resultado_sub.configure(
            text=(
                f"{resultado.cantidad} valores · {resumen_parametros(resultado)} · "
                f"{resultado.decimales} decimales"
            )
        )
        self._habilitar_acciones(True)

        estadisticas = calcular_estadisticas(resultado)
        compacto = self.winfo_width() < 1360
        fila_stats = tk.Frame(self.results_body, bg=WHITE)
        fila_stats.pack(fill="x", pady=(0, 10))
        for i in range(4):
            fila_stats.grid_columnconfigure(i, weight=1, uniform="stats")

        tarjeta_media = TarjetaEstadistica(
            fila_stats, "Media", self.fuente_ui, self.fuente_mono, compacta=compacto
        )
        tarjeta_media.actualizar(
            formato_u(estadisticas.media, 4),
            "≈ 0,5" if compacto else "uniforme ≈ 0,5",
        )

        tarjeta_var = TarjetaEstadistica(
            fila_stats, "Varianza", self.fuente_ui, self.fuente_mono, compacta=compacto
        )
        tarjeta_var.actualizar(
            formato_u(estadisticas.varianza, 4),
            "ideal 0,083" if compacto else f"σ {formato_u(estadisticas.desviacion, 3)} · ideal 0,083",
        )

        tarjeta_rango = TarjetaEstadistica(
            fila_stats, "Rango de U", self.fuente_ui, self.fuente_mono, compacta=compacto
        )
        tarjeta_rango.actualizar(
            (
                f"{formato_u(estadisticas.minimo, 2)}–{formato_u(estadisticas.maximo, 2)}"
                if compacto
                else f"{formato_u(estadisticas.minimo, 3)} – {formato_u(estadisticas.maximo, 3)}"
            ),
            "mín. y máx." if compacto else "mín. y máx. observados",
            tamano=10 if compacto else 12,
        )

        valor_periodo, detalle_periodo = texto_periodo(resultado)
        tarjeta_periodo = TarjetaEstadistica(
            fila_stats, "Periodo", self.fuente_ui, self.fuente_mono, compacta=compacto
        )
        tamano_periodo = 14 if len(valor_periodo) <= 8 else 11
        if compacto and detalle_periodo.startswith("teórico"):
            detalle_periodo = "teórico"
        tarjeta_periodo.actualizar(valor_periodo, detalle_periodo, tamano=tamano_periodo)

        for indice, tarjeta in enumerate(
            (tarjeta_media, tarjeta_var, tarjeta_rango, tarjeta_periodo)
        ):
            tarjeta.grid(
                row=0,
                column=indice,
                sticky="nsew",
                padx=(0 if indice == 0 else 5, 0 if indice == 3 else 5),
            )

        if resultado.advertencias:
            self._crear_avisos(resultado)

        self._crear_notebook(resultado)

    def _crear_avisos(self, resultado: Resultado) -> None:
        marcadores = (
            "ciclo",
            "llegó a 0",
            "no cumplen",
            "no es primo",
            "no es raíz",
            "no son coprimos",
            "puede ser menor",
            "se acorta",
            "degeneración",
            "punto fijo",
            "fijo en",
        )
        tiene_problema = any(
            marcador in aviso.lower()
            for aviso in resultado.advertencias
            for marcador in marcadores
        )
        if tiene_problema:
            fondo, borde, color, color_texto = AMBER_SOFT, AMBER_LINE, AMBER, "#92400e"
            titulo = "AVISOS DEL GENERADOR"
        else:
            fondo, borde, color, color_texto = BLUE_SOFT, "#bfdbfe", BLUE, "#1e40af"
            titulo = "NOTA DEL GENERADOR"

        marco = tk.Frame(
            self.results_body,
            bg=fondo,
            highlightthickness=1,
            highlightbackground=borde,
        )
        marco.pack(fill="x", pady=(0, 10))
        interior = tk.Frame(marco, bg=fondo)
        interior.pack(fill="x", padx=11, pady=8)
        tk.Label(
            interior,
            text=titulo,
            bg=fondo,
            fg=color,
            font=(self.fuente_ui, 7, "bold"),
            anchor="w",
        ).pack(fill="x")
        for aviso in resultado.advertencias[:3]:
            tk.Label(
                interior,
                text=f"•  {aviso}",
                bg=fondo,
                fg=color_texto,
                font=(self.fuente_ui, 8),
                anchor="w",
                justify="left",
                wraplength=790,
            ).pack(fill="x", pady=(1, 0))
        self._hacer_texto_ajustable(interior, margen=42, minimo=300)

    def _crear_notebook(self, resultado: Resultado) -> None:
        self._notebook = ttk.Notebook(self.results_body)
        self._notebook.pack(fill="both", expand=True)

        tab_pasos = tk.Frame(self._notebook, bg=WHITE)
        tab_tabla = tk.Frame(self._notebook, bg=WHITE)
        tab_graficas = tk.Frame(self._notebook, bg=WHITE)
        tab_metodo = tk.Frame(self._notebook, bg=WHITE)
        self._tab_graficas = tab_graficas
        self._tab_metodo = tab_metodo

        self._notebook.add(tab_pasos, text="Paso a paso")
        self._notebook.add(tab_tabla, text="Tabla")
        self._notebook.add(tab_graficas, text="Gráficas")
        self._notebook.add(tab_metodo, text="El método")

        self._crear_tab_pasos(tab_pasos, resultado)
        self._crear_tab_tabla(tab_tabla, resultado)
        self._crear_tab_graficas(tab_graficas, resultado)
        self._crear_tab_metodo(tab_metodo, resultado)

        self._notebook.bind("<<NotebookTabChanged>>", self._al_cambiar_tab)

    def _crear_tab_pasos(self, padre: tk.Misc, resultado: Resultado) -> None:
        marco = MarcoDesplazable(padre, WHITE)
        marco.pack(fill="both", expand=True, pady=(10, 0))
        self._pasos_marco = marco
        interior = marco.interior

        resumen = tk.Frame(interior, bg="#f0fdfa", highlightthickness=1, highlightbackground=ACCENT_LINE)
        resumen.pack(fill="x", pady=(0, 10))
        tk.Label(
            resumen,
            text="CÓMO SE CALCULÓ CADA NÚMERO",
            bg="#f0fdfa",
            fg=ACCENT_DARK,
            font=(self.fuente_ui, 7, "bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(8, 0))
        detalle = (
            f"{resultado.cantidad} pasos · {resumen_parametros(resultado)} · "
            f"U se muestra con {resultado.decimales} decimales"
        )
        tk.Label(
            resumen,
            text=detalle,
            bg="#f0fdfa",
            fg="#276b65",
            font=(self.fuente_ui, 8),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(1, 8))

        for paso in resultado.pasos[:40]:
            self._crear_tarjeta_paso(interior, paso, resultado)

        if len(resultado.pasos) > 40:
            tk.Label(
                interior,
                text=(
                    f"Se muestran los primeros 40 de {len(resultado.pasos)} pasos. "
                    "La pestaña «Tabla» y la exportación CSV contienen la secuencia completa."
                ),
                bg=WHITE,
                fg=MUTED,
                font=(self.fuente_ui, 8),
                anchor="w",
                justify="left",
                wraplength=640,
            ).pack(fill="x", pady=(2, 8))

        if resultado.periodo is not None and resultado.inicio_periodo is not None:
            tk.Label(
                interior,
                text=(
                    f"El ciclo empieza en {notacion_de_paso(resultado, resultado.inicio_periodo)} "
                    f"y se repite cada {resultado.periodo} pasos."
                ),
                bg=WHITE,
                fg=AMBER,
                font=(self.fuente_ui, 8),
                anchor="w",
            ).pack(fill="x", pady=(2, 10))

        tk.Frame(interior, bg=WHITE, height=8).pack(fill="x")

    def _crear_tarjeta_paso(self, padre: tk.Misc, paso: Paso, resultado: Resultado) -> None:
        en_ciclo = (
            resultado.periodo is not None
            and resultado.inicio_periodo is not None
            and paso.indice >= resultado.inicio_periodo
        )
        fondo = "#fffdf5" if en_ciclo else PANEL
        borde = AMBER_LINE if en_ciclo else LINE

        tarjeta = tk.Frame(
            padre,
            bg=fondo,
            highlightthickness=1,
            highlightbackground=borde,
        )
        tarjeta.pack(fill="x", pady=(0, 9))

        cabecera = tk.Frame(tarjeta, bg=fondo)
        cabecera.pack(fill="x", padx=13, pady=(10, 0))
        tk.Label(
            cabecera,
            text=f"PASO {paso.indice:02d}",
            bg=fondo,
            fg=ACCENT_DARK if not en_ciclo else AMBER,
            font=(self.fuente_ui, 7, "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            cabecera,
            text=f"estado {paso.notacion}",
            bg=fondo,
            fg=MUTED_2,
            font=(self.fuente_ui, 8),
            anchor="w",
        ).pack(side="left", padx=(8, 0))
        tk.Label(
            cabecera,
            text=f"U = {formato_u(paso.u, resultado.decimales)}",
            bg=fondo,
            fg=ACCENT_DARK if not en_ciclo else AMBER,
            font=(self.fuente_mono, 12, "bold"),
            anchor="e",
        ).pack(side="right")

        formula = tk.Label(
            tarjeta,
            text=paso.formula,
            bg=fondo,
            fg=NAVY,
            font=(self.fuente_ui, 9, "bold"),
            anchor="w",
            justify="left",
            wraplength=600,
        )
        formula.pack(fill="x", padx=13, pady=(3, 7))

        detalle = tk.Frame(tarjeta, bg=fondo)
        detalle.pack(fill="x", padx=13, pady=(0, 9))
        detalle.grid_columnconfigure(0, minsize=150, weight=0)
        detalle.grid_columnconfigure(1, weight=1)
        for fila, (etiqueta, valor) in enumerate(paso.detalle):
            tk.Label(
                detalle,
                text=etiqueta,
                bg=fondo,
                fg=MUTED,
                font=(self.fuente_ui, 8),
                anchor="w",
            ).grid(row=fila, column=0, sticky="nw", pady=1)
            tk.Label(
                detalle,
                text=valor,
                bg=fondo,
                fg=TEXT,
                font=(self.fuente_mono, 8),
                anchor="w",
                justify="left",
                wraplength=480,
            ).grid(row=fila, column=1, sticky="nw", pady=1, padx=(8, 0))

        if paso.nota:
            tk.Label(
                tarjeta,
                text=f"⚠  {paso.nota}",
                bg=fondo,
                fg=AMBER,
                font=(self.fuente_ui, 8),
                anchor="w",
                justify="left",
                wraplength=600,
            ).pack(fill="x", padx=13, pady=(0, 9))

    def _crear_tab_tabla(self, padre: tk.Misc, resultado: Resultado) -> None:
        contenedor = tk.Frame(padre, bg=WHITE)
        contenedor.pack(fill="both", expand=True, pady=(10, 0))

        marco_tree = tk.Frame(contenedor, bg=WHITE, highlightthickness=1, highlightbackground=LINE)
        marco_tree.pack(fill="both", expand=True)
        marco_tree.grid_rowconfigure(0, weight=1)
        marco_tree.grid_columnconfigure(0, weight=1)

        columnas = ("paso", "estado", "x", "u")
        self.tabla = ttk.Treeview(
            marco_tree,
            columns=columnas,
            show="headings",
            selectmode="browse",
        )
        self.tabla.heading("paso", text="PASO")
        self.tabla.heading("estado", text="ESTADO")
        self.tabla.heading("x", text="VALOR x")
        self.tabla.heading("u", text="U NORMALIZADA")
        self.tabla.column("paso", width=50, anchor="center", stretch=False)
        self.tabla.column("estado", width=65, anchor="center", stretch=False)
        self.tabla.column("x", width=140, anchor="e")
        self.tabla.column("u", width=150, anchor="e")

        scroll = ttk.Scrollbar(marco_tree, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=scroll.set)
        self.tabla.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        self.tabla.tag_configure("par", background="#fbfcfe")
        self.tabla.tag_configure("impar", background=WHITE)
        self.tabla.tag_configure("ciclo", background="#fff8e6")

        for paso in resultado.pasos:
            tag = "par" if paso.indice % 2 == 0 else "impar"
            if (
                resultado.periodo is not None
                and resultado.inicio_periodo is not None
                and paso.indice >= resultado.inicio_periodo
            ):
                tag = "ciclo"
            self.tabla.insert(
                "",
                "end",
                values=(
                    f"{paso.indice:02d}",
                    paso.notacion,
                    formato_entero(paso.valor),
                    formato_u(paso.u, resultado.decimales),
                ),
                tags=(tag,),
            )

        pie = tk.Frame(contenedor, bg=WHITE)
        pie.pack(fill="x", pady=(8, 0))
        nota = (
            "Las filas resaltadas pertenecen al ciclo detectado."
            if resultado.periodo is not None
            else "La tabla contiene todos los valores generados."
        )
        tk.Label(
            pie,
            text=nota,
            bg=WHITE,
            fg=MUTED,
            font=(self.fuente_ui, 8),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            pie,
            text=f"{resultado.cantidad} filas",
            bg=WHITE,
            fg=MUTED_2,
            font=(self.fuente_ui, 8),
            anchor="e",
        ).pack(side="right")

    def _crear_tab_graficas(self, padre: tk.Misc, resultado: Resultado) -> None:
        contenedor = MarcoDesplazable(padre, WHITE)
        contenedor.pack(fill="both", expand=True, pady=(10, 0))
        interior = contenedor.interior

        self._crear_tarjeta_grafica(
            interior,
            "Distribución de U",
            "10 intervalos de igual anchura · la línea punteada marca la frecuencia esperada",
            GraficaHistograma,
            resultado,
            175,
        )
        self._crear_tarjeta_grafica(
            interior,
            "Secuencia generada",
            "Cada punto es un Uₙ · la línea punteada es la media observada",
            GraficaSecuencia,
            resultado,
            165,
        )

    def _crear_tarjeta_grafica(
        self,
        padre: tk.Misc,
        titulo: str,
        subtitulo: str,
        clase,
        resultado: Resultado,
        alto: int,
    ) -> None:
        tarjeta = tk.Frame(padre, bg=WHITE, highlightthickness=1, highlightbackground=LINE)
        tarjeta.pack(fill="x", pady=(0, 12))
        cabecera = tk.Frame(tarjeta, bg=WHITE)
        cabecera.pack(fill="x", padx=13, pady=(10, 0))
        tk.Label(
            cabecera,
            text=titulo,
            bg=WHITE,
            fg=NAVY,
            font=(self.fuente_ui, 10, "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            cabecera,
            text=subtitulo,
            bg=WHITE,
            fg=MUTED_2,
            font=(self.fuente_ui, 7),
            anchor="e",
        ).pack(side="right")
        grafica = clase(tarjeta, self.fuente_ui, alto=alto)
        grafica.pack(fill="x", padx=10, pady=(4, 10))
        grafica.establecer_datos(resultado)
        self._graficas.append(grafica)

    def _crear_tab_metodo(self, padre: tk.Misc, resultado: Resultado) -> None:
        marco = MarcoDesplazable(padre, WHITE)
        marco.pack(fill="both", expand=True, pady=(10, 0))
        interior = marco.interior
        metodo = resultado.metodo

        formula = tk.Frame(interior, bg="#f0fdfa", highlightthickness=1, highlightbackground=ACCENT_LINE)
        formula.pack(fill="x", pady=(0, 12))
        tk.Label(
            formula,
            text="FÓRMULA DEL MÉTODO",
            bg="#f0fdfa",
            fg=ACCENT_DARK,
            font=(self.fuente_ui, 7, "bold"),
            anchor="w",
        ).pack(fill="x", padx=13, pady=(9, 0))
        tk.Label(
            formula,
            text=metodo.formula,
            bg="#f0fdfa",
            fg="#0f5f59",
            font=(self.fuente_mono, 10, "bold"),
            anchor="w",
            justify="left",
            wraplength=720,
        ).pack(fill="x", padx=13, pady=(2, 10))

        tk.Label(
            interior,
            text="La idea",
            bg=WHITE,
            fg=NAVY,
            font=(self.fuente_ui, 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 3))
        tk.Label(
            interior,
            text=metodo.idea,
            bg=WHITE,
            fg=MUTED,
            font=(self.fuente_ui, 9),
            anchor="w",
            justify="left",
            wraplength=760,
        ).pack(fill="x", pady=(0, 13))

        tk.Label(
            interior,
            text="Algoritmo paso a paso",
            bg=WHITE,
            fg=NAVY,
            font=(self.fuente_ui, 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))
        for numero, texto in enumerate(metodo.pasos, 1):
            fila = tk.Frame(interior, bg=WHITE)
            fila.pack(fill="x", pady=1)
            tk.Label(
                fila,
                text=str(numero),
                bg=ACCENT_SOFT,
                fg=ACCENT_DARK,
                font=(self.fuente_mono, 8, "bold"),
                width=3,
                pady=2,
            ).pack(side="left", anchor="n")
            tk.Label(
                fila,
                text=texto,
                bg=WHITE,
                fg=TEXT,
                font=(self.fuente_ui, 9),
                anchor="w",
                justify="left",
                wraplength=700,
            ).pack(side="left", fill="x", padx=(9, 0), pady=(2, 2))

        tk.Label(
            interior,
            text="Condiciones y recomendaciones",
            bg=WHITE,
            fg=NAVY,
            font=(self.fuente_ui, 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(14, 4))
        for texto in metodo.condiciones:
            tk.Label(
                interior,
                text=f"•  {texto}",
                bg=WHITE,
                fg=MUTED,
                font=(self.fuente_ui, 9),
                anchor="w",
                justify="left",
                wraplength=740,
            ).pack(fill="x", pady=1)

        actual = tk.Frame(interior, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        actual.pack(fill="x", pady=(14, 8))
        tk.Label(
            actual,
            text="EN ESTA EJECUCIÓN",
            bg=PANEL,
            fg=MUTED_2,
            font=(self.fuente_ui, 7, "bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(8, 2))
        periodo_valor, periodo_detalle = texto_periodo(resultado)
        textos = [
            f"Parámetros: {resumen_parametros(resultado)}.",
            f"Periodo observado: {periodo_valor} ({periodo_detalle}).",
            f"Fuente: {metodo.fuente}",
        ]
        for texto in textos:
            tk.Label(
                actual,
                text=texto,
                bg=PANEL,
                fg=MUTED,
                font=(self.fuente_ui, 8),
                anchor="w",
                justify="left",
                wraplength=730,
            ).pack(fill="x", padx=12, pady=(0, 3))
        tk.Frame(actual, bg=PANEL, height=4).pack(fill="x")

        tk.Label(
            interior,
            text="La aplicación implementa estas operaciones con enteros de Python; "
            "no se usa random(), numpy ni scipy para generar los valores.",
            bg=WHITE,
            fg=MUTED_2,
            font=(self.fuente_ui, 8),
            anchor="w",
            justify="left",
            wraplength=740,
        ).pack(fill="x", pady=(2, 12))
        self._hacer_texto_ajustable(interior)

    def _al_cambiar_tab(self, _event=None) -> None:
        if self._notebook is None:
            return
        try:
            actual = self._notebook.select()
            tab = self.nametowidget(actual)
        except Exception:
            return
        if tab is self._tab_graficas:
            for grafica in self._graficas:
                grafica._programar()

    # -- acciones ------------------------------------------------------------

    def _texto_tabla(self, separador: str = "\t") -> str:
        if self.resultado is None:
            return ""
        lineas = [separador.join(("Paso", "Estado", "x_n", "U_n"))]
        for paso in self.resultado.pasos:
            lineas.append(
                separador.join(
                    (
                        str(paso.indice),
                        paso.notacion,
                        str(paso.valor),
                        formato_u(paso.u, self.resultado.decimales),
                    )
                )
            )
        return "\n".join(lineas)

    def copiar_tabla(self) -> None:
        if self.resultado is None:
            return
        self.clipboard_clear()
        self.clipboard_append(self._texto_tabla())
        self._avisar_boton(self.btn_copiar, "¡Copiado!")

    def exportar_csv(self) -> None:
        if self.resultado is None:
            return
        nombre = f"aleatorios_{self.resultado.metodo.id}_{datetime.now():%Y%m%d_%H%M}.csv"
        ruta = filedialog.asksaveasfilename(
            parent=self,
            title="Exportar secuencia",
            defaultextension=".csv",
            initialfile=nombre,
            filetypes=(("Archivo CSV", "*.csv"), ("Todos los archivos", "*.*")),
        )
        if not ruta:
            return
        try:
            with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
                escritor = csv.writer(archivo, delimiter=";")
                escritor.writerow(("Paso", "Estado", "x_n", "U_n", "Metodo"))
                for paso in self.resultado.pasos:
                    escritor.writerow(
                        (
                            paso.indice,
                            paso.notacion,
                            paso.valor,
                            formato_u(paso.u, self.resultado.decimales),
                            self.resultado.metodo.nombre,
                        )
                    )
            self._avisar_boton(self.btn_exportar, "Guardado")
        except OSError as error:
            messagebox.showerror(
                "No se pudo exportar",
                f"No se pudo guardar el archivo:\n\n{error}",
                parent=self,
            )

    def _avisar_boton(self, boton: Boton, texto: str) -> None:
        original = boton.cget("text")
        boton.configure(text=texto)
        self.after(1200, lambda: boton.configure(text=original) if boton.winfo_exists() else None)

    # -- guía ---------------------------------------------------------------

    def abrir_guia(self) -> None:
        VentanaGuia(self, self.fuente_ui, self.fuente_mono)


# ---------------------------------------------------------------------------
# Ventana de ayuda
# ---------------------------------------------------------------------------


class VentanaGuia(tk.Toplevel):
    def __init__(self, parent: tk.Misc, fuente_ui: str, fuente_mono: str) -> None:
        super().__init__(parent)
        self.title("Guía rápida · AleatoriaLab")
        self.configure(bg=WHITE)
        self.geometry("760x690")
        self.minsize(640, 540)
        self.transient(parent)
        self.grab_set()
        self._fuente_ui = fuente_ui
        self._fuente_mono = fuente_mono

        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - 760) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - 690) // 2)
        self.geometry(f"760x690+{x}+{y}")

        cabecera = tk.Frame(self, bg=NAVY)
        cabecera.pack(fill="x")
        tk.Label(
            cabecera,
            text="AleatoriaLab",
            bg=NAVY,
            fg="#ffffff",
            font=(fuente_ui, 15, "bold"),
            anchor="w",
        ).pack(fill="x", padx=24, pady=(16, 0))
        tk.Label(
            cabecera,
            text="Guía rápida para leer y usar la calculadora",
            bg=NAVY,
            fg="#a9bfd4",
            font=(fuente_ui, 9),
            anchor="w",
        ).pack(fill="x", padx=24, pady=(2, 16))

        contenedor = tk.Frame(self, bg=WHITE)
        contenedor.pack(fill="both", expand=True, padx=20, pady=(12, 0))

        texto = tk.Text(
            contenedor,
            bg=WHITE,
            fg=TEXT,
            relief="flat",
            bd=0,
            wrap="word",
            font=(fuente_ui, 9),
            padx=4,
            pady=4,
            cursor="arrow",
        )
        scroll = ttk.Scrollbar(contenedor, orient="vertical", command=texto.yview)
        texto.configure(yscrollcommand=scroll.set)
        texto.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        texto.tag_configure(
            "h",
            font=(fuente_ui, 11, "bold"),
            foreground=NAVY,
            spacing1=12,
            spacing3=4,
        )
        texto.tag_configure(
            "body",
            font=(fuente_ui, 9),
            foreground="#475569",
            spacing3=4,
        )
        texto.tag_configure(
            "formula",
            font=(fuente_mono, 9),
            foreground=ACCENT_DARK,
            background="#f0fdfa",
            spacing1=2,
            spacing3=5,
            lmargin1=10,
            lmargin2=10,
        )
        texto.tag_configure(
            "small",
            font=(fuente_ui, 8),
            foreground=MUTED_2,
            spacing3=2,
        )

        self._texto = texto
        self._insertar_contenido()
        texto.configure(state="disabled")

        pie = tk.Frame(self, bg=WHITE)
        pie.pack(fill="x", padx=20, pady=(8, 16))
        Boton(
            pie,
            texto="Cerrar",
            comando=self.destroy,
            variante="primary",
            fuente=(fuente_ui, 9, "bold"),
            padx=18,
            pady=8,
        ).pack(side="right")
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(80, self._enfocar)

    def _enfocar(self) -> None:
        try:
            self.focus_set()
        except tk.TclError:
            pass

    def _insertar_contenido(self) -> None:
        t = self._texto
        t.insert("end", "Qué hace esta aplicación\n", "h")
        t.insert(
            "end",
            "Genera secuencias de números pseudoaleatorios en el intervalo [0, 1) "
            "con siete métodos clásicos de simulación. El motor está escrito con "
            "aritmética entera propia: no se usa random(), numpy ni scipy para "
            "calcular los valores. La interfaz solo presenta los cálculos.\n",
            "body",
        )

        t.insert("end", "Cómo leer un resultado\n", "h")
        t.insert(
            "end",
            "Cada fila de «Paso a paso» muestra el estado xₙ, la fórmula aplicada, "
            "las operaciones intermedias y el valor normalizado Uₙ = xₙ / m. "
            "La pestaña «Tabla» reúne la secuencia completa y «Gráficas» permite "
            "comparar la distribución con una uniforme ideal.\n",
            "body",
        )

        t.insert("end", "Los siete métodos\n", "h")
        for metodo in METODOS:
            t.insert("end", f"• {metodo.nombre} — {metodo.resumen}\n", "body")
            t.insert("end", f"  {metodo.formula}\n", "formula")

        t.insert("end", "Cómo elegir parámetros\n", "h")
        t.insert(
            "end",
            "Para el congruencial lineal, Hull–Dobell da condiciones suficientes "
            "para periodo completo. En el multiplicativo conviene un módulo primo "
            "y un multiplicador que sea raíz primitiva. En los métodos de centro "
            "y en el cuadrático no hay garantía de periodo largo: revisa el aviso "
            "y la tarjeta «Periodo».\n",
            "body",
        )
        t.insert(
            "end",
            "Atajos: Ctrl + Enter genera, Ctrl + S exporta y F1 abre esta guía. "
            "El botón «Copiar tabla» deja los datos en el portapapeles.\n",
            "body",
        )

        t.insert("end", "Buenas prácticas\n", "h")
        t.insert(
            "end",
            "• Una semilla distinta produce otra secuencia, pero la secuencia sigue siendo determinista.\n"
            "• No uses estos métodos para criptografía: son generadores didácticos.\n"
            "• Comprueba siempre el periodo y la distribución antes de usar una secuencia en un modelo.\n"
            "• En simulación real se prefieren generadores modernos auditados; aquí el objetivo es entender el cálculo.\n",
            "body",
        )

        t.insert("end", "Bibliografía de apoyo\n", "h")
        referencias = (
            "Raúl Coss Bu — Simulación (capítulo 2, generación de números aleatorios).",
            "Sheldon M. Ross — Simulación, 2.ª ed. (capítulo 3, números aleatorios).",
            "Agustín Jiménez Avello et al. — Simulación de procesos y aplicaciones.",
            "Eduardo García Dunna et al. — Simulación y análisis de sistemas con ProModel.",
            "Simulation and Modeling to Understand the Change (2021 y 2022).",
            "Técnicas de Simulación y Remuestreo con R.",
        )
        for referencia in referencias:
            t.insert("end", f"• {referencia}\n", "body")
        t.insert(
            "end",
            "\nMaterial de apoyo del curso. Esta aplicación es independiente de "
            "las obras citadas y no reproduce su contenido.\n",
            "small",
        )


# ---------------------------------------------------------------------------
# Arranque
# ---------------------------------------------------------------------------


def iniciar() -> None:
    app = Aplicacion()
    app.mainloop()
