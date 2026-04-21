"""
tela_dados.py — Painel "Dados Carregados" e "Relatório de Inconsistências".

TelaDados       Sub-notebook com uma aba por entidade (Professores, Disciplinas,
                Salas, Turmas) mais uma aba de Inconsistências do LeitorCSV.

TelaRelatorio   Aba separada que exibe as falhas e avisos gerados pelo
                GeradorDeGrade após a geração da grade.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Optional

from organizador_aulas.gui.componentes import TabelaTV, PainelVazio
from organizador_aulas.gui.estilos import CORES, FONTES

if TYPE_CHECKING:
    from organizador_aulas.leitor_csv import ResultadoLeitura
    from organizador_aulas.gerador.gerador_de_grade import ResultadoGrade


# ── TelaDados ─────────────────────────────────────────────────────────────────

class TelaDados(ttk.Frame):
    """
    Painel principal de visualização dos dados carregados pelo LeitorCSV.

    Organizado como um sub-notebook com 5 abas:
        Professores | Disciplinas | Salas | Turmas | Inconsistências
    """

    def __init__(self, parent: tk.Widget, app) -> None:
        super().__init__(parent, style="TFrame")
        self._app = app
        self._construir()

    def _construir(self) -> None:
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill=tk.BOTH, expand=True)

        # Aba Professores
        frame_p = ttk.Frame(self._nb, style="TFrame")
        self._nb.add(frame_p, text="  👨‍🏫 Professores  ")
        self._tv_prof = TabelaTV(
            frame_p,
            colunas=["ID", "Nome", "Dias Disponíveis", "Qtd. Dias"],
            larguras=[55, 220, 300, 90],
        )
        self._tv_prof.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Aba Disciplinas
        frame_d = ttk.Frame(self._nb, style="TFrame")
        self._nb.add(frame_d, text="  📖 Disciplinas  ")
        self._tv_disc = TabelaTV(
            frame_d,
            colunas=["ID", "Nome", "Blocos/Sem", "Min/Sem", "Professor"],
            larguras=[55, 230, 90, 80, 220],
        )
        self._tv_disc.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Aba Salas
        frame_s = ttk.Frame(self._nb, style="TFrame")
        self._nb.add(frame_s, text="  🏫 Salas  ")
        self._tv_salas = TabelaTV(
            frame_s,
            colunas=["ID", "Número", "Capacidade"],
            larguras=[55, 140, 110],
        )
        self._tv_salas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Aba Turmas
        frame_t = ttk.Frame(self._nb, style="TFrame")
        self._nb.add(frame_t, text="  👥 Turmas  ")
        self._tv_turmas = TabelaTV(
            frame_t,
            colunas=["ID", "Nome", "Curso", "Disciplinas", "Alunos"],
            larguras=[55, 170, 250, 90, 70],
        )
        self._tv_turmas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Aba Inconsistências
        frame_i = ttk.Frame(self._nb, style="TFrame")
        self._nb.add(frame_i, text="  ⚠️ Inconsistências  ")
        self._construir_aba_inconsistencias(frame_i)

    def _construir_aba_inconsistencias(self, parent: ttk.Frame) -> None:
        # Cabeçalho resumo
        self._frame_resumo_inc = tk.Frame(parent, bg=CORES["bg_app"], pady=12, padx=16)
        self._frame_resumo_inc.pack(fill=tk.X)
        self._lbl_resumo_inc = tk.Label(
            self._frame_resumo_inc,
            text="Carregue os CSVs para visualizar inconsistências.",
            bg=CORES["bg_app"],
            fg=CORES["texto_secundario"],
            font=FONTES["corpo"],
            anchor="w",
        )
        self._lbl_resumo_inc.pack(anchor="w")

        # Tabela de inconsistências
        self._tv_inconsist = TabelaTV(
            parent,
            colunas=["Tipo", "Mensagem"],
            larguras=[70, 800],
        )
        self._tv_inconsist.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

    # ------------------------------------------------------------------
    # Atualização de dados
    # ------------------------------------------------------------------

    def atualizar(
        self,
        rl: "ResultadoLeitura",
        professores_nome: Optional[dict] = None,
    ) -> None:
        """Popula todas as abas com os dados do ResultadoLeitura."""
        self._popular_professores(rl)
        self._popular_disciplinas(rl)
        self._popular_salas(rl)
        self._popular_turmas(rl)
        self._popular_inconsistencias(rl)

    def _popular_professores(self, rl: "ResultadoLeitura") -> None:
        linhas = []
        for p in sorted(rl.professores.values(), key=lambda x: x.id_professor):
            dias = ", ".join(p.dias_disponiveis) if p.dias_disponiveis else "—"
            linhas.append([p.id_professor, p.nome, dias, len(p.dias_disponiveis)])
        self._tv_prof.popular(linhas)

    def _popular_disciplinas(self, rl: "ResultadoLeitura") -> None:
        linhas = []
        for d in sorted(rl.disciplinas.values(), key=lambda x: x.id_disciplina):
            prof_nome = "—"
            if d.id_professor and d.id_professor in rl.professores:
                prof_nome = rl.professores[d.id_professor].nome
            linhas.append([
                d.id_disciplina, d.nome,
                d.carga_horaria_semanal, d.carga_horaria_minutos,
                prof_nome,
            ])
        self._tv_disc.popular(linhas)

    def _popular_salas(self, rl: "ResultadoLeitura") -> None:
        linhas = [
            [s.id_sala, s.numero, s.capacidade]
            for s in sorted(rl.salas.values(), key=lambda x: x.id_sala)
        ]
        self._tv_salas.popular(linhas)

    def _popular_turmas(self, rl: "ResultadoLeitura") -> None:
        linhas = []
        for t in sorted(rl.turmas.values(), key=lambda x: x.id_turma):
            linhas.append([
                t.id_turma, t.nome, t.curso,
                len(t.id_disciplinas), t.quantidade_alunos,
            ])
        self._tv_turmas.popular(linhas)

    def _popular_inconsistencias(self, rl: "ResultadoLeitura") -> None:
        n = len(rl.inconsistencias)
        if n == 0:
            self._lbl_resumo_inc.config(
                text="✅  Nenhuma inconsistência detectada nos CSVs.",
                fg=CORES["sucesso"],
            )
        else:
            self._lbl_resumo_inc.config(
                text=f"⚠️  {n} inconsistência(s) encontrada(s) nos arquivos CSV.",
                fg=CORES["aviso"],
            )

        linhas = []
        tags = []
        for msg in rl.inconsistencias:
            if msg.startswith("❌"):
                tipo = "ERRO"
                tags.append("erro")
            else:
                tipo = "AVISO"
                tags.append("aviso")
            mensagem = msg.split(":", 1)[-1].strip() if ":" in msg else msg
            linhas.append([tipo, mensagem])
        self._tv_inconsist.popular(linhas, tags)


# ── TelaRelatorio ─────────────────────────────────────────────────────────────

class TelaRelatorio(ttk.Frame):
    """
    Painel que exibe o relatório completo pós-geração de grade:
    - Resumo (blocos alocados, status)
    - Avisos (não-críticos)
    - Falhas de alocação com diagnóstico detalhado
    """

    def __init__(self, parent: tk.Widget, app) -> None:
        super().__init__(parent, style="TFrame")
        self._app = app
        self._construir()

    def _construir(self) -> None:
        # Cabeçalho de resumo
        self._frame_resumo = tk.Frame(self, bg=CORES["bg_app"], padx=16, pady=12)
        self._frame_resumo.pack(fill=tk.X)

        self._lbl_status = tk.Label(
            self._frame_resumo,
            text="Grade ainda não gerada.",
            bg=CORES["bg_app"],
            fg=CORES["texto_secundario"],
            font=FONTES["subtitulo"],
            anchor="w",
        )
        self._lbl_status.pack(anchor="w")

        self._lbl_detalhe = tk.Label(
            self._frame_resumo,
            text="Carregue os CSVs e clique em 'Gerar Grade' para iniciar.",
            bg=CORES["bg_app"],
            fg=CORES["texto_secundario"],
            font=FONTES["pequena"],
            anchor="w",
        )
        self._lbl_detalhe.pack(anchor="w", pady=(4, 0))

        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=8)

        # Notebook interno: Avisos + Falhas
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill=tk.BOTH, expand=True)

        frame_av = ttk.Frame(self._nb)
        self._nb.add(frame_av, text="  ℹ️ Avisos  ")
        self._tv_avisos = TabelaTV(
            frame_av,
            colunas=["Mensagem"],
            larguras=[900],
        )
        self._tv_avisos.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        frame_fa = ttk.Frame(self._nb)
        self._nb.add(frame_fa, text="  ❌ Falhas de Alocação  ")
        self._tv_falhas = TabelaTV(
            frame_fa,
            colunas=["Mensagem"],
            larguras=[900],
        )
        self._tv_falhas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def atualizar(self, rg: "ResultadoGrade") -> None:
        """Popula o relatório com os dados do ResultadoGrade."""
        # Status
        if rg.completa:
            self._lbl_status.config(
                text=f"✅  Grade COMPLETA — {rg.total_blocos_alocados} blocos alocados.",
                fg=CORES["sucesso"],
            )
        else:
            pct = (
                rg.total_blocos_alocados / rg.total_blocos_necessarios * 100
                if rg.total_blocos_necessarios > 0
                else 0
            )
            self._lbl_status.config(
                text=f"⚠️  Grade PARCIAL — {rg.total_blocos_alocados}/"
                     f"{rg.total_blocos_necessarios} blocos ({pct:.1f}%).",
                fg=CORES["aviso"],
            )

        self._lbl_detalhe.config(
            text=f"Aulas geradas: {len(rg.aulas)}  |  "
                 f"Falhas: {len(rg.falhas)}  |  Avisos: {len(rg.avisos)}",
            fg=CORES["texto_secundario"],
        )

        # Avisos
        self._tv_avisos.popular([[v] for v in rg.avisos],
                                tags=["aviso"] * len(rg.avisos))

        # Falhas
        tags_falha = [
            "erro" if msg.startswith("❌") else "aviso"
            for msg in rg.falhas
        ]
        self._tv_falhas.popular([[f] for f in rg.falhas], tags=tags_falha)

        # Notifica abas
        qtd_av = len(rg.avisos)
        qtd_fa = len(rg.falhas)
        self._nb.tab(0, text=f"  ℹ️ Avisos ({qtd_av})  ")
        self._nb.tab(1, text=f"  ❌ Falhas ({qtd_fa})  ")
