"""
tela_grade.py — Painel de visualização da grade horária gerada.

TelaGradeEntidade   Tela genérica que exibe a grade semanal para uma entidade
                    selecionada (modo 'turma' ou 'professor'). Contém:
                    • Combobox de seleção da entidade
                    • Painel de informações resumidas
                    • Grade visual semanal (GradeVisual) com scroll
                    • Legenda de disciplinas coloridas
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Dict, List, Optional

from organizador_aulas.gui.componentes import GradeVisual, PainelVazio
from organizador_aulas.gui.estilos import CORES, FONTES, cor_disciplina

if TYPE_CHECKING:
    from organizador_aulas.gerador.gerador_de_grade import ResultadoGrade
    from organizador_aulas.leitor_csv import ResultadoLeitura


class TelaGradeEntidade(ttk.Frame):
    """
    Painel de grade horária por entidade (turma ou professor).

    Layout
    ------
    ┌─ Toolbar ──────────────────────────────────────────────┐
    │  [Selecionar:] [Combobox▾]  ⬡ Info resumida da entidade│
    ├─ Grade semanal (scrollável) ───────────────────────────┤
    │  Seg | Ter | Qua | Qui | Sex                           │
    │  Bloco 1 …                                             │
    │  …                                                     │
    ├─ Legenda de disciplinas ───────────────────────────────┤
    └────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        parent: tk.Widget,
        app,
        modo: str = "turma",   # "turma" | "professor"
    ) -> None:
        super().__init__(parent, style="TFrame")
        self._app = app
        self._modo = modo
        self._rg: Optional[ResultadoGrade] = None
        self._rl: Optional[ResultadoLeitura] = None

        # Mapa: string do combobox → ID da entidade
        self._mapa_ids: Dict[str, int] = {}

        self._construir()

    def _construir(self) -> None:
        # ── Toolbar ──────────────────────────────────────────────────────────
        toolbar = tk.Frame(self, bg=CORES["bg_app"], pady=10, padx=16)
        toolbar.pack(fill=tk.X)

        label_texto = "Turma:" if self._modo == "turma" else "Professor:"
        tk.Label(
            toolbar, text=label_texto,
            bg=CORES["bg_app"], fg=CORES["texto_primario"],
            font=FONTES["corpo_bold"],
        ).pack(side=tk.LEFT)

        self._combo_var = tk.StringVar()
        self._combo = ttk.Combobox(
            toolbar,
            textvariable=self._combo_var,
            font=FONTES["corpo"],
            width=35,
            state="readonly",
        )
        self._combo.pack(side=tk.LEFT, padx=8)
        self._combo.bind("<<ComboboxSelected>>", self._on_selecao)

        # Info resumida
        self._lbl_info = tk.Label(
            toolbar,
            text="",
            bg=CORES["bg_app"],
            fg=CORES["texto_secundario"],
            font=FONTES["pequena"],
            anchor="w",
        )
        self._lbl_info.pack(side=tk.LEFT, padx=12)

        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=8)

        # ── Painel principal: grade ou placeholder ────────────────────────────
        self._frame_conteudo = tk.Frame(self, bg=CORES["bg_app"])
        self._frame_conteudo.pack(fill=tk.BOTH, expand=True)

        self._painel_vazio = PainelVazio(
            self._frame_conteudo,
            "📅",
            "Nenhuma entidade selecionada",
            "Gere a grade e selecione uma entidade no menu acima.",
        )
        self._painel_vazio.pack(fill=tk.BOTH, expand=True)

        # Container para grade scrollável (montado sob demanda)
        self._frame_grade = tk.Frame(self._frame_conteudo, bg=CORES["bg_app"])
        self._canvas = tk.Canvas(
            self._frame_grade,
            bg=CORES["bg_card"],
            highlightthickness=0,
        )
        self._sb_h = ttk.Scrollbar(self._frame_grade, orient="horizontal",
                                   command=self._canvas.xview)
        self._sb_v = ttk.Scrollbar(self._frame_grade, orient="vertical",
                                   command=self._canvas.yview)
        self._canvas.configure(
            yscrollcommand=self._sb_v.set,
            xscrollcommand=self._sb_h.set,
        )
        self._sb_h.pack(side=tk.BOTTOM, fill=tk.X)
        self._sb_v.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Frame interno do canvas
        self._frame_interno = tk.Frame(self._canvas, bg=CORES["bg_card"])
        self._canvas.create_window((0, 0), window=self._frame_interno, anchor="nw")
        self._frame_interno.bind(
            "<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")
            ),
        )
        # Bind scroll com roda do mouse
        self._canvas.bind("<Enter>", self._ativar_scroll_mouse)
        self._canvas.bind("<Leave>", self._desativar_scroll_mouse)

        self._grade: Optional[GradeVisual] = None

        # ── Legenda ──────────────────────────────────────────────────────────
        self._frame_legenda = tk.Frame(self, bg=CORES["bg_app"], padx=12, pady=6)
        self._frame_legenda.pack(fill=tk.X, side=tk.BOTTOM)

    # ── Scroll com roda do mouse ──────────────────────────────────────────────

    def _ativar_scroll_mouse(self, event) -> None:
        self._canvas.bind_all("<MouseWheel>", self._scroll_vertical)
        self._canvas.bind_all("<Shift-MouseWheel>", self._scroll_horizontal)

    def _desativar_scroll_mouse(self, event) -> None:
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Shift-MouseWheel>")

    def _scroll_vertical(self, event) -> None:
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _scroll_horizontal(self, event) -> None:
        self._canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── Atualização ──────────────────────────────────────────────────────────

    def atualizar(self, rg: "ResultadoGrade", rl: "ResultadoLeitura") -> None:
        """
        Recebe os resultados e recarrega o combobox de seleção.
        Chamado pelo App após a geração.
        """
        self._rg = rg
        self._rl = rl
        self._mapa_ids = {}
        opcoes: List[str] = []

        if self._modo == "turma":
            for t in sorted(rl.turmas.values(), key=lambda x: x.nome):
                chave = f"{t.nome}  —  {t.curso}"
                opcoes.append(chave)
                self._mapa_ids[chave] = t.id_turma
        else:
            for p in sorted(rl.professores.values(), key=lambda x: x.nome):
                chave = f"{p.nome}"
                opcoes.append(chave)
                self._mapa_ids[chave] = p.id_professor

        self._combo.config(values=opcoes, state="readonly")
        self._combo_var.set("")
        self._lbl_info.config(text="")
        self._grade = None
        self._mostrar_vazio()

    def _on_selecao(self, event=None) -> None:
        """Chamado quando o usuário seleciona uma entidade no combobox."""
        valor = self._combo_var.get()
        if not valor or not self._rg:
            return
        id_entidade = self._mapa_ids.get(valor)
        if id_entidade is None:
            return
        self._exibir_grade(id_entidade)


    def _exibir_grade(self, id_entidade: int) -> None:
        """Filtra as aulas e renderiza a grade para a entidade selecionada."""
        if self._modo == "turma":
            aulas = self._rg.aulas_por_turma(id_entidade)
            entidade = self._rl.turmas.get(id_entidade)
            if entidade:
                self._lbl_info.config(
                    text=f"Curso: {entidade.curso}  |  "
                         f"{entidade.quantidade_alunos} alunos  |  "
                         f"{entidade.total_disciplinas} disciplinas  |  "
                         f"{len(aulas)} blocos alocados"
                )
        else:
            aulas = self._rg.aulas_por_professor(id_entidade)
            entidade = self._rl.professores.get(id_entidade)
            if entidade:
                dias = ", ".join(entidade.dias_disponiveis)
                self._lbl_info.config(
                    text=f"Dias: {dias}  |  {len(aulas)} blocos alocados"
                )

        # Determina blocos necessários
        n_blocos = max(
            (a.horario.numero_bloco for a in aulas),
            default=8,
        )
        n_blocos = max(n_blocos, 8)

        # Cria ou recria a GradeVisual
        if self._grade is not None:
            self._grade.destroy()
        self._grade = GradeVisual(
            self._frame_interno,
            n_blocos=n_blocos,
            modo=self._modo,
        )
        self._grade.pack(padx=8, pady=8, anchor="nw")
        self._grade.atualizar(aulas)
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

        # Exibe o frame de grade
        self._mostrar_grade()

        # Atualiza legenda
        self._atualizar_legenda(aulas)

    def _mostrar_vazio(self) -> None:
        self._frame_grade.pack_forget()
        self._frame_legenda.pack_forget()
        self._painel_vazio.pack(fill=tk.BOTH, expand=True)

    def _mostrar_grade(self) -> None:
        self._painel_vazio.pack_forget()
        self._frame_grade.pack(fill=tk.BOTH, expand=True)
        self._frame_legenda.pack(fill=tk.X, side=tk.BOTTOM)

    def _atualizar_legenda(self, aulas) -> None:
        """Reconstrói a legenda de cores de disciplinas."""
        for widget in self._frame_legenda.winfo_children():
            widget.destroy()

        tk.Label(
            self._frame_legenda, text="Legenda: ",
            bg=CORES["bg_app"],
            fg=CORES["texto_secundario"],
            font=FONTES["pequena_bold"],
        ).pack(side=tk.LEFT)

        vistas: set[int] = set()
        for aula in sorted(aulas, key=lambda a: a.disciplina.nome):
            id_d = aula.disciplina.id_disciplina
            if id_d in vistas:
                continue
            vistas.add(id_d)
            bg, fg = cor_disciplina(id_d)
            tk.Label(
                self._frame_legenda,
                text=f"  {aula.disciplina.nome}  ",
                bg=bg, fg=fg,
                font=FONTES["pequena_bold"],
                padx=6, pady=2,
                relief="flat",
            ).pack(side=tk.LEFT, padx=3)
