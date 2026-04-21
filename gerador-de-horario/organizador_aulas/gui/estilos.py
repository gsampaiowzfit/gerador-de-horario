"""
estilos.py — Sistema de design centralizado da interface Tkinter.

Define todas as constantes de cor, fontes e a configuração do tema ttk.
Ao centralizar aqui, qualquer ajuste visual é feito em um único lugar.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# ── Paleta de cores ────────────────────────────────────────────────────────────

CORES: dict[str, str] = {
    # Estrutura principal
    "bg_app":               "#f1f5f9",
    "bg_card":              "#ffffff",
    "bg_header":            "#1e3a5f",
    "bg_sidebar":           "#1e3a5f",
    "bg_sidebar_sec":       "#162e4d",

    # Acento e interação
    "accent":               "#2563eb",
    "accent_hover":         "#1d4ed8",
    "accent_light":         "#eff6ff",

    # Tipografia
    "texto_primario":       "#0f172a",
    "texto_secundario":     "#64748b",
    "texto_header":         "#ffffff",
    "texto_sidebar":        "#94a3b8",
    "texto_sidebar_titulo": "#cbd5e1",

    # Bordas
    "borda":                "#e2e8f0",
    "borda_sidebar":        "#2d4a6b",

    # Feedback
    "sucesso":              "#16a34a",
    "sucesso_bg":           "#dcfce7",
    "erro":                 "#dc2626",
    "erro_bg":              "#fee2e2",
    "aviso":                "#d97706",
    "aviso_bg":             "#fef3c7",

    # Grade visual
    "celula_vazia":         "#f8fafc",
    "celula_borda":         "#e2e8f0",
    "grade_header":         "#1e3a5f",

    # Treeview
    "tv_row_par":           "#f8fafc",
    "tv_row_impar":         "#ffffff",
}

# ── Paleta de cores para disciplinas (bg, fg) ─────────────────────────────────

CORES_DISCIPLINAS: list[tuple[str, str]] = [
    ("#dbeafe", "#1e40af"),   # azul
    ("#dcfce7", "#166534"),   # verde
    ("#fef3c7", "#92400e"),   # âmbar
    ("#fce7f3", "#9d174d"),   # rosa
    ("#ede9fe", "#5b21b6"),   # violeta
    ("#cffafe", "#164e63"),   # ciano
    ("#ffedd5", "#7c2d12"),   # laranja
    ("#f0fdf4", "#14532d"),   # esmeralda
    ("#fdf4ff", "#6b21a8"),   # púrpura
    ("#fff7ed", "#9a3412"),   # âmbar-escuro
]

# ── Fontes ─────────────────────────────────────────────────────────────────────

_F = "Segoe UI"

FONTES: dict[str, tuple] = {
    "titulo_app":     (_F, 15, "bold"),
    "titulo":         (_F, 13, "bold"),
    "subtitulo":      (_F, 11, "bold"),
    "corpo":          (_F, 10),
    "corpo_bold":     (_F, 10, "bold"),
    "pequena":        (_F, 9),
    "pequena_bold":   (_F, 9, "bold"),
    "btn":            (_F, 10, "bold"),
    "status":         (_F, 9),
    "sidebar_sec":    (_F, 8, "bold"),
    "sidebar_item":   (_F, 10),
    "grade_disc":     (_F, 8, "bold"),
    "grade_info":     (_F, 8),
    "grade_header":   (_F, 9, "bold"),
    "grade_bloco":    (_F, 8),
}

# ── Helpers ────────────────────────────────────────────────────────────────────


def cor_disciplina(id_disciplina: int) -> tuple[str, str]:
    """Retorna (bg, fg) para colorir um bloco de disciplina na grade."""
    return CORES_DISCIPLINAS[id_disciplina % len(CORES_DISCIPLINAS)]


def configurar_tema(root: tk.Tk) -> None:
    """
    Aplica o tema ttk personalizado à janela raiz.
    Deve ser chamado uma única vez, após criar tk.Tk().
    """
    style = ttk.Style(root)
    style.theme_use("clam")

    # ── Frames ───────────────────────────────────────────────────────────────
    style.configure("TFrame", background=CORES["bg_app"])
    style.configure("Card.TFrame", background=CORES["bg_card"])

    # ── Labels ───────────────────────────────────────────────────────────────
    style.configure("TLabel",
                    background=CORES["bg_app"],
                    foreground=CORES["texto_primario"],
                    font=FONTES["corpo"])
    style.configure("Titulo.TLabel",
                    background=CORES["bg_app"],
                    foreground=CORES["texto_primario"],
                    font=FONTES["titulo"])
    style.configure("Card.TLabel",
                    background=CORES["bg_card"],
                    foreground=CORES["texto_primario"],
                    font=FONTES["corpo"])
    style.configure("Secundario.TLabel",
                    background=CORES["bg_app"],
                    foreground=CORES["texto_secundario"],
                    font=FONTES["pequena"])

    # ── Notebook ─────────────────────────────────────────────────────────────
    style.configure("TNotebook",
                    background=CORES["bg_app"],
                    borderwidth=0,
                    tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab",
                    background=CORES["borda"],
                    foreground=CORES["texto_secundario"],
                    font=FONTES["corpo"],
                    padding=(16, 8),
                    borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", CORES["bg_card"]),
                          ("active", CORES["accent_light"])],
              foreground=[("selected", CORES["accent"]),
                          ("active", CORES["accent"])])

    # ── Treeview ─────────────────────────────────────────────────────────────
    style.configure("Treeview",
                    font=FONTES["corpo"],
                    rowheight=30,
                    background=CORES["bg_card"],
                    fieldbackground=CORES["bg_card"],
                    foreground=CORES["texto_primario"],
                    borderwidth=0,
                    relief="flat")
    style.configure("Treeview.Heading",
                    font=FONTES["corpo_bold"],
                    background=CORES["bg_header"],
                    foreground="white",
                    relief="flat",
                    padding=(8, 6))
    style.map("Treeview",
              background=[("selected", CORES["accent"])],
              foreground=[("selected", "white")])
    style.map("Treeview.Heading",
              background=[("active", CORES["accent_hover"])])

    # ── Scrollbar ────────────────────────────────────────────────────────────
    style.configure("TScrollbar",
                    background=CORES["borda"],
                    troughcolor=CORES["bg_app"],
                    borderwidth=0,
                    arrowsize=11,
                    relief="flat")

    # ── Combobox ─────────────────────────────────────────────────────────────
    style.configure("TCombobox",
                    font=FONTES["corpo"],
                    background=CORES["bg_card"],
                    foreground=CORES["texto_primario"],
                    padding=(8, 4),
                    relief="solid",
                    borderwidth=1)

    # ── Separator ────────────────────────────────────────────────────────────
    style.configure("TSeparator", background=CORES["borda"])

    # ── Spinbox ──────────────────────────────────────────────────────────────
    style.configure("TSpinbox",
                    font=FONTES["corpo"],
                    background=CORES["bg_card"],
                    foreground=CORES["texto_primario"])
