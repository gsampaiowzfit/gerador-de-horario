"""
componentes.py — Widgets reutilizáveis da interface.

Classes
-------
TabelaTV       Treeview com scrollbars integradas e coloração de linhas pares/ímpares.
GradeVisual    Tabela semanal de blocos de 50 min com células coloridas por disciplina.
PainelVazio    Placeholder exibido quando não há dados carregados/gerados.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Tuple

from organizador_aulas.models.aula import Aula
from organizador_aulas.models.horario import Horario
from organizador_aulas.gui.estilos import CORES, FONTES, cor_disciplina

# Dias na ordem de exibição da grade
DIAS_SEMANA = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta"]
ALIAS_DIA = {
    "Segunda": "Seg",
    "Terca":   "Ter",
    "Quarta":  "Qua",
    "Quinta":  "Qui",
    "Sexta":   "Sex",
    "Sabado":  "Sáb",
}


# ── TabelaTV ──────────────────────────────────────────────────────────────────

class TabelaTV(ttk.Frame):
    """
    Treeview com barra de rolagem vertical e horizontal integradas.

    Parâmetros
    ----------
    colunas : list[str]
        Nomes dos cabeçalhos de coluna.
    larguras : list[int] | None
        Largura em pixels de cada coluna. Se None, todas recebem 120.
    altura_linhas : int
        Altura de cada linha da tabela (overrides ttk style se necessário).
    """

    def __init__(
        self,
        parent: tk.Widget,
        colunas: List[str],
        larguras: Optional[List[int]] = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self._colunas = colunas
        self._larguras = larguras or [120] * len(colunas)
        self._construir()

    def _construir(self) -> None:
        # Scrollbars
        sb_v = ttk.Scrollbar(self, orient="vertical")
        sb_h = ttk.Scrollbar(self, orient="horizontal")
        sb_v.grid(row=0, column=1, sticky="ns")
        sb_h.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Treeview
        self._tv = ttk.Treeview(
            self,
            columns=self._colunas,
            show="headings",
            yscrollcommand=sb_v.set,
            xscrollcommand=sb_h.set,
            selectmode="browse",
        )
        self._tv.grid(row=0, column=0, sticky="nsew")
        sb_v.config(command=self._tv.yview)
        sb_h.config(command=self._tv.xview)

        # Configure columns
        for col, larg in zip(self._colunas, self._larguras):
            self._tv.heading(col, text=col, anchor="w")
            self._tv.column(col, width=larg, minwidth=40, anchor="w")

        # Row colors
        self._tv.tag_configure("par",   background=CORES["tv_row_par"])
        self._tv.tag_configure("impar", background=CORES["tv_row_impar"])
        self._tv.tag_configure("erro",  background=CORES["erro_bg"],
                               foreground=CORES["erro"])
        self._tv.tag_configure("aviso", background=CORES["aviso_bg"],
                               foreground=CORES["aviso"])
        self._tv.tag_configure("ok",    background=CORES["sucesso_bg"],
                               foreground=CORES["sucesso"])

    def limpar(self) -> None:
        """Remove todas as linhas da tabela."""
        self._tv.delete(*self._tv.get_children())

    def adicionar_linha(
        self,
        valores: List[str | int],
        tag: str = "",
    ) -> None:
        """
        Adiciona uma linha à tabela.

        Parâmetros
        ----------
        valores : list
            Lista de valores correspondentes às colunas.
        tag : str
            Tag para coloração: 'par', 'impar', 'erro', 'aviso', 'ok' ou ''.
        """
        n = len(self._tv.get_children())
        if not tag:
            tag = "par" if n % 2 == 0 else "impar"
        self._tv.insert("", "end", values=[str(v) for v in valores], tags=(tag,))

    def popular(
        self,
        linhas: List[List[str | int]],
        tags: Optional[List[str]] = None,
    ) -> None:
        """Limpa e reinsere todas as linhas de uma vez."""
        self.limpar()
        for i, linha in enumerate(linhas):
            tag = tags[i] if tags else ""
            self.adicionar_linha(linha, tag)

    @property
    def treeview(self) -> ttk.Treeview:
        return self._tv


# ── GradeVisual ───────────────────────────────────────────────────────────────

class GradeVisual(tk.Frame):
    """
    Tabela semanal de aulas no formato timetable clássico.

    Linhas  = blocos de 50 min (1 … n_blocos)
    Colunas = dias da semana

    Células coloridas por disciplina (paleta automática).
    """

    _LARG_BLOCO = 42      # coluna "Bloco"
    _LARG_HORA  = 78      # coluna "Horário"
    _LARG_DIA   = 148     # colunas de dias
    _ALT_HEADER = 36
    _ALT_CELULA = 62

    def __init__(
        self,
        parent: tk.Widget,
        n_blocos: int = 8,
        modo: str = "turma",   # "turma" | "professor"
        dias: Optional[List[str]] = None,
    ) -> None:
        super().__init__(parent, bg=CORES["bg_card"])
        self._n_blocos = n_blocos
        self._modo = modo
        self._dias = dias or DIAS_SEMANA
        self._celulas: dict[tuple[str, int], tk.Label] = {}
        self._construir()

    def _construir(self) -> None:
        # Configurar grid
        self.columnconfigure(0, minsize=self._LARG_BLOCO)
        self.columnconfigure(1, minsize=self._LARG_HORA)
        for c in range(2, 2 + len(self._dias)):
            self.columnconfigure(c, minsize=self._LARG_DIA, weight=1)
        for r in range(self._n_blocos + 1):
            self.rowconfigure(
                r,
                minsize=self._ALT_HEADER if r == 0 else self._ALT_CELULA,
            )

        # Header
        self._lbl_cabecalho(0, 0, "Bloco")
        self._lbl_cabecalho(0, 1, "Horário")
        for c, dia in enumerate(self._dias, 2):
            self._lbl_cabecalho(0, c, ALIAS_DIA.get(dia, dia))

        # Linhas de blocos
        for bloco in range(1, self._n_blocos + 1):
            h = Horario(dia=self._dias[0], numero_bloco=bloco)

            # Coluna bloco
            tk.Label(
                self, text=str(bloco),
                bg=CORES["celula_vazia"],
                fg=CORES["texto_secundario"],
                font=FONTES["grade_bloco"],
                relief="flat",
            ).grid(row=bloco, column=0, sticky="nsew", padx=1, pady=1)

            # Coluna horário
            tk.Label(
                self, text=f"{h.hora_inicio}\n{h.hora_fim}",
                bg=CORES["celula_vazia"],
                fg=CORES["texto_secundario"],
                font=FONTES["grade_bloco"],
                justify="center",
                relief="flat",
            ).grid(row=bloco, column=1, sticky="nsew", padx=1, pady=1)

            # Células de dias
            for c, dia in enumerate(self._dias, 2):
                cell = tk.Label(
                    self,
                    text="",
                    bg=CORES["celula_vazia"],
                    fg=CORES["texto_primario"],
                    wraplength=self._LARG_DIA - 10,
                    justify="center",
                    font=FONTES["grade_disc"],
                    relief="flat",
                    padx=4, pady=4,
                )
                cell.grid(row=bloco, column=c, sticky="nsew", padx=1, pady=1)
                self._celulas[(dia, bloco)] = cell

    def _lbl_cabecalho(self, row: int, col: int, texto: str) -> None:
        tk.Label(
            self,
            text=texto,
            bg=CORES["grade_header"],
            fg="white",
            font=FONTES["grade_header"],
            anchor="center",
        ).grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

    def limpar(self) -> None:
        """Limpa todas as células da grade."""
        for cell in self._celulas.values():
            cell.config(text="", bg=CORES["celula_vazia"], fg=CORES["texto_primario"])

    def atualizar(self, aulas: List[Aula]) -> None:
        """Repopula a grade com as aulas fornecidas."""
        self.limpar()
        for aula in aulas:
            chave = (aula.horario.dia, aula.horario.numero_bloco)
            if chave not in self._celulas:
                continue
            bg, fg = cor_disciplina(aula.disciplina.id_disciplina)
            self._celulas[chave].config(
                text=self._texto(aula),
                bg=bg,
                fg=fg,
            )

    def _texto(self, aula: Aula) -> str:
        if self._modo == "turma":
            disc = self._truncar(aula.disciplina.nome, 22)
            info = f"{aula.professor.nome.split()[0]} · {aula.sala.numero}"
        else:  # professor
            disc = self._truncar(aula.turma.nome, 20)
            info = f"{self._truncar(aula.disciplina.nome, 20)}\n{aula.sala.numero}"
        return f"{disc}\n{info}"

    @staticmethod
    def _truncar(texto: str, n: int) -> str:
        return texto[:n] + "…" if len(texto) > n else texto


# ── PainelVazio ───────────────────────────────────────────────────────────────

class PainelVazio(ttk.Frame):
    """
    Placeholder exibido quando não há dados disponíveis para o painel.
    Mostra um ícone grande + mensagem descritiva.
    """

    def __init__(self, parent: tk.Widget, icone: str, titulo: str, detalhe: str) -> None:
        super().__init__(parent, style="TFrame")
        self.pack_propagate(True)

        frame = tk.Frame(self, bg=CORES["bg_app"])
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text=icone, bg=CORES["bg_app"],
                 font=("Segoe UI", 40)).pack(pady=(0, 12))
        tk.Label(frame, text=titulo, bg=CORES["bg_app"],
                 fg=CORES["texto_primario"],
                 font=FONTES["subtitulo"]).pack()
        tk.Label(frame, text=detalhe, bg=CORES["bg_app"],
                 fg=CORES["texto_secundario"],
                 font=FONTES["pequena"], justify="center",
                 wraplength=320).pack(pady=(6, 0))
