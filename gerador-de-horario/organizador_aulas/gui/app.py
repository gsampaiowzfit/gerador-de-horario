"""
app.py — Janela principal do Organizador de Aulas.

Orquestra toda a interface: header com botões de ação, sidebar com status,
notebook central com 4 abas e barra de status inferior.
A geração da grade roda em thread separada para não congelar a interface.
"""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from organizador_aulas.gerador.gerador_de_grade import GeradorDeGrade, ResultadoGrade
from organizador_aulas.gui.estilos import CORES, FONTES, configurar_tema
from organizador_aulas.gui.tela_dados import TelaDados, TelaRelatorio
from organizador_aulas.gui.tela_grade import TelaGradeEntidade
from organizador_aulas.leitor_csv import LeitorCSV, ResultadoLeitura


class App(tk.Tk):
    """Janela principal do sistema Organizador de Aulas."""

    _LARGURA_SIDEBAR = 220

    def __init__(self) -> None:
        super().__init__()
        self.title("Organizador de Aulas")
        self.geometry("1300x820")
        self.minsize(960, 640)
        self.configure(bg=CORES["bg_header"])

        # ── Estado da aplicação ──────────────────────────────────────────────
        self._rl: Optional[ResultadoLeitura] = None
        self._rg: Optional[ResultadoGrade] = None
        self._paths: Dict[str, str] = {}
        self._fila: queue.Queue = queue.Queue()

        # ── Configurações de geração ─────────────────────────────────────────
        self._var_blocos = tk.IntVar(value=8)
        self._var_max_iter = tk.IntVar(value=50_000)
        self._vars_dias: Dict[str, tk.BooleanVar] = {
            "Segunda": tk.BooleanVar(value=True),
            "Terca":   tk.BooleanVar(value=True),
            "Quarta":  tk.BooleanVar(value=True),
            "Quinta":  tk.BooleanVar(value=True),
            "Sexta":   tk.BooleanVar(value=True),
            "Sabado":  tk.BooleanVar(value=False),
        }

        configurar_tema(self)
        self._construir_ui()

    # ── Construção da UI ──────────────────────────────────────────────────────

    def _construir_ui(self) -> None:
        # Header
        self._criar_header().pack(fill=tk.X)

        # Corpo: sidebar + notebook
        corpo = tk.Frame(self, bg=CORES["bg_app"])
        corpo.pack(fill=tk.BOTH, expand=True)

        self._criar_sidebar(corpo).pack(side=tk.LEFT, fill=tk.Y)
        tk.Frame(corpo, bg=CORES["borda_sidebar"], width=1).pack(side=tk.LEFT, fill=tk.Y)

        # Notebook
        frame_nb = tk.Frame(corpo, bg=CORES["bg_app"])
        frame_nb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._nb = ttk.Notebook(frame_nb)
        self._nb.pack(fill=tk.BOTH, expand=True)

        self._tela_dados = TelaDados(self._nb, self)
        self._tela_relatorio = TelaRelatorio(self._nb, self)
        self._tela_grade_turma = TelaGradeEntidade(self._nb, self, modo="turma")
        self._tela_grade_prof = TelaGradeEntidade(self._nb, self, modo="professor")

        self._nb.add(self._tela_dados,       text="  📊 Dados Carregados  ")
        self._nb.add(self._tela_grade_turma, text="  📅 Grade por Turma  ")
        self._nb.add(self._tela_grade_prof,  text="  👩‍🏫 Grade por Professor  ")
        self._nb.add(self._tela_relatorio,   text="  📋 Relatório  ")

        # Barra de status
        self._var_status = tk.StringVar(
            value="Pronto. Clique em '📂 Carregar CSVs' para começar."
        )
        barra = tk.Frame(self, bg=CORES["bg_app"], pady=5, padx=14,
                         relief="flat", bd=0)
        barra.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Frame(barra, bg=CORES["borda"], height=1).pack(fill=tk.X, side=tk.TOP)
        tk.Label(
            barra,
            textvariable=self._var_status,
            bg=CORES["bg_app"],
            fg=CORES["texto_secundario"],
            font=FONTES["status"],
            anchor="w",
        ).pack(fill=tk.X, pady=(4, 0))

    # ── Header ────────────────────────────────────────────────────────────────

    def _criar_header(self) -> tk.Frame:
        header = tk.Frame(self, bg=CORES["bg_header"], height=64)
        header.pack_propagate(False)

        # Marca
        marca = tk.Frame(header, bg=CORES["bg_header"])
        marca.pack(side=tk.LEFT, padx=20, pady=8)
        tk.Label(
            marca, text="📅  Organizador de Aulas",
            bg=CORES["bg_header"], fg="white",
            font=FONTES["titulo_app"],
        ).pack(side=tk.LEFT)
        tk.Label(
            marca, text=" — Sistema Automático de Grade Horária",
            bg=CORES["bg_header"], fg=CORES["texto_sidebar"],
            font=FONTES["pequena"],
        ).pack(side=tk.LEFT)

        # Botões (da direita para a esquerda)
        acoes = tk.Frame(header, bg=CORES["bg_header"])
        acoes.pack(side=tk.RIGHT, padx=16, pady=10)

        self._btn_exportar = self._btn_header(
            acoes, "💾  Exportar", self._acao_exportar, "#16a34a", "#15803d"
        )
        self._btn_gerar = self._btn_header(
            acoes, "▶  Gerar Grade", self._acao_gerar_grade,
            CORES["accent"], CORES["accent_hover"],
        )
        self._btn_config = self._btn_header(
            acoes, "⚙️  Config", self._acao_configuracoes,
            "#475569", "#334155",
        )
        self._btn_carregar = self._btn_header(
            acoes, "📂  Carregar CSVs", self._acao_carregar_csvs,
            "#475569", "#334155",
        )
        return header

    @staticmethod
    def _btn_header(parent, texto, cmd, bg, bg_active) -> tk.Button:
        btn = tk.Button(
            parent, text=texto, command=cmd,
            bg=bg, fg="white", font=FONTES["btn"],
            bd=0, padx=14, pady=6, cursor="hand2",
            activebackground=bg_active, activeforeground="white",
        )
        btn.pack(side=tk.RIGHT, padx=4)
        return btn

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _criar_sidebar(self, parent: tk.Frame) -> tk.Frame:
        sb = tk.Frame(parent, bg=CORES["bg_sidebar"], width=self._LARGURA_SIDEBAR)
        sb.pack_propagate(False)

        # Seção: dados carregados
        self._lbl_dados: Dict[str, tk.Label] = {}
        self._sec_sidebar(sb, "DADOS CARREGADOS")
        for chave, label, icone in [
            ("professores", "Professores", "👨‍🏫"),
            ("disciplinas", "Disciplinas", "📖"),
            ("salas",       "Salas",       "🏫"),
            ("turmas",      "Turmas",      "👥"),
        ]:
            row = tk.Frame(sb, bg=CORES["bg_sidebar"])
            row.pack(fill=tk.X, padx=16, pady=2)
            tk.Label(
                row, text=f"{icone}  {label}",
                bg=CORES["bg_sidebar"], fg=CORES["texto_sidebar"],
                font=FONTES["sidebar_item"], anchor="w",
            ).pack(side=tk.LEFT)
            lbl = tk.Label(
                row, text="—",
                bg=CORES["bg_sidebar"], fg=CORES["texto_sidebar"],
                font=FONTES["pequena"],
            )
            lbl.pack(side=tk.RIGHT)
            self._lbl_dados[chave] = lbl

        # Ícone de inconsistências
        row_inc = tk.Frame(sb, bg=CORES["bg_sidebar"])
        row_inc.pack(fill=tk.X, padx=16, pady=2)
        tk.Label(
            row_inc, text="⚠️  Inconsistências",
            bg=CORES["bg_sidebar"], fg=CORES["texto_sidebar"],
            font=FONTES["sidebar_item"], anchor="w",
        ).pack(side=tk.LEFT)
        self._lbl_inc = tk.Label(
            row_inc, text="—",
            bg=CORES["bg_sidebar"], fg=CORES["texto_sidebar"],
            font=FONTES["pequena"],
        )
        self._lbl_inc.pack(side=tk.RIGHT)

        # Seção: grade horária
        self._var_grade_status = tk.StringVar(value="Não gerada")
        self._var_grade_blocos = tk.StringVar(value="—")
        self._var_grade_falhas = tk.StringVar(value="—")

        self._sec_sidebar(sb, "GRADE HORÁRIA")
        for var, label in [
            (self._var_grade_status, "Status"),
            (self._var_grade_blocos, "Blocos"),
            (self._var_grade_falhas, "Falhas"),
        ]:
            row = tk.Frame(sb, bg=CORES["bg_sidebar"])
            row.pack(fill=tk.X, padx=16, pady=2)
            tk.Label(
                row, text=label,
                bg=CORES["bg_sidebar"], fg=CORES["texto_sidebar"],
                font=FONTES["sidebar_item"], anchor="w",
            ).pack(side=tk.LEFT)
            tk.Label(
                row, textvariable=var,
                bg=CORES["bg_sidebar"], fg=CORES["texto_sidebar"],
                font=FONTES["pequena"],
            ).pack(side=tk.RIGHT)

        return sb

    @staticmethod
    def _sec_sidebar(parent: tk.Frame, titulo: str) -> None:
        tk.Frame(parent, bg=CORES["borda_sidebar"], height=1).pack(
            fill=tk.X, pady=(16, 0)
        )
        tk.Label(
            parent, text=titulo,
            bg=CORES["bg_sidebar"], fg=CORES["texto_sidebar"],
            font=FONTES["sidebar_sec"],
        ).pack(anchor="w", padx=16, pady=(8, 4))

    # ── Ações ─────────────────────────────────────────────────────────────────

    def _acao_carregar_csvs(self) -> None:
        """Abre o diálogo de seleção de CSVs e carrega os dados."""
        from organizador_aulas.gui.dialogo_carregar import DialogoCarregarCSV

        dialogo = DialogoCarregarCSV(self)
        self.wait_window(dialogo)

        if dialogo.resultado is None:
            return  # cancelado

        self._paths = dialogo.resultado
        self._set_status("Lendo arquivos CSV…")
        self.update_idletasks()

        # Resolve paths para o LeitorCSV
        caminho_pasta = Path(next(iter(self._paths.values()))).parent \
            if self._paths else Path(".")

        leitor = LeitorCSV(pasta_csv=caminho_pasta)
        rl = leitor.carregar_tudo(
            path_professores=self._paths.get("professores") or None,
            path_disciplinas=self._paths.get("disciplinas") or None,
            path_turmas=self._paths.get("turmas") or None,
            path_salas=self._paths.get("salas") or None,
        )

        self._rl = rl
        self._rg = None  # Invalida grade anterior
        self._atualizar_sidebar_dados()
        self._tela_dados.atualizar(rl)

        n_inc = len(rl.inconsistencias)
        if n_inc:
            self._set_status(
                f"⚠️  CSVs carregados com {n_inc} inconsistência(s). "
                "Revise a aba 'Dados Carregados > Inconsistências'."
            )
        else:
            self._set_status(
                f"✅  CSVs carregados com sucesso — "
                f"{len(rl.professores)} professores, "
                f"{len(rl.disciplinas)} disciplinas, "
                f"{len(rl.salas)} salas, "
                f"{len(rl.turmas)} turmas."
            )

    def _acao_gerar_grade(self) -> None:
        """Inicia a geração da grade em thread separada."""
        if not self._rl:
            messagebox.showwarning(
                "Atenção",
                "Carregue os arquivos CSV primeiro.",
                parent=self,
            )
            return

        if not self._rl.turmas:
            messagebox.showerror(
                "Erro",
                "Nenhuma turma foi carregada. Verifique o arquivo Turmas.csv.",
                parent=self,
            )
            return

        dias_selecionados = [
            dia for dia, var in self._vars_dias.items() if var.get()
        ]
        if not dias_selecionados:
            messagebox.showerror(
                "Erro",
                "Selecione ao menos um dia letivo em ⚙️ Config.",
                parent=self,
            )
            return

        self._btn_gerar.config(state="disabled", text="⏳  Gerando…")
        self._set_status("Gerando grade horária… Aguarde.")
        self.update_idletasks()

        parametros = {
            "dias_letivos": dias_selecionados,
            "blocos_por_dia": self._var_blocos.get(),
            "max_iteracoes_backtrack": self._var_max_iter.get(),
            "preferir_dias_distintos": True,
        }

        def tarefa() -> None:
            try:
                gerador = GeradorDeGrade(self._rl, **parametros)
                resultado = gerador.gerar()
                self._fila.put(("ok", resultado))
            except Exception as exc:
                import traceback
                self._fila.put(("erro", traceback.format_exc()))

        threading.Thread(target=tarefa, daemon=True).start()
        self.after(100, self._verificar_fila_geracao)

    def _verificar_fila_geracao(self) -> None:
        """Monitora a fila de resultado da geração (chamado via after)."""
        try:
            tipo, dados = self._fila.get_nowait()
        except queue.Empty:
            self.after(100, self._verificar_fila_geracao)
            return

        self._btn_gerar.config(state="normal", text="▶  Gerar Grade")

        if tipo == "ok":
            self._rg = dados
            self._atualizar_sidebar_grade()
            self._tela_relatorio.atualizar(dados)
            self._tela_grade_turma.atualizar(dados, self._rl)
            self._tela_grade_prof.atualizar(dados, self._rl)

            if dados.completa:
                self._nb.tab(1, text="  📅 Grade por Turma  ")
                self._nb.select(1)
                self._set_status(
                    f"✅  Grade COMPLETA — {dados.total_blocos_alocados} blocos "
                    f"alocados em {len(dados.aulas)} aulas."
                )
            else:
                self._nb.tab(3, text="  📋 Relatório ⚠️  ")
                self._nb.select(3)
                self._set_status(
                    f"⚠️  Grade PARCIAL — "
                    f"{dados.total_blocos_alocados}/{dados.total_blocos_necessarios} "
                    f"blocos. Veja o Relatório para detalhes."
                )
        else:
            messagebox.showerror(
                "Erro na geração",
                f"Ocorreu um erro inesperado:\n\n{dados}",
                parent=self,
            )
            self._set_status("❌ Falha na geração. Consulte o log de erros.")

    def _acao_exportar(self) -> None:
        """Exporta a grade gerada para um arquivo CSV via pandas."""
        if not self._rg or not self._rg.aulas:
            messagebox.showwarning(
                "Atenção",
                "Gere a grade antes de exportar.",
                parent=self,
            )
            return

        caminho = filedialog.asksaveasfilename(
            title="Salvar grade como CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="grade_gerada.csv",
        )
        if not caminho:
            return

        try:
            df = self._rg.to_dataframe()
            df.to_csv(caminho, index=False, encoding="utf-8-sig")
            messagebox.showinfo(
                "Exportado",
                f"Grade exportada com sucesso!\n{caminho}",
                parent=self,
            )
            self._set_status(f"✅  Grade exportada para: {caminho}")
        except Exception as exc:
            messagebox.showerror(
                "Erro ao exportar",
                f"Não foi possível salvar o arquivo:\n{exc}",
                parent=self,
            )

    def _acao_configuracoes(self) -> None:
        """Abre o diálogo de configurações de geração."""
        from organizador_aulas.gui.dialogo_carregar import DialogoConfiguracoes

        dialogo = DialogoConfiguracoes(
            self,
            var_blocos=self._var_blocos,
            var_max_iter=self._var_max_iter,
            vars_dias=self._vars_dias,
        )
        self.wait_window(dialogo)

    # ── Atualização de estado na UI ───────────────────────────────────────────

    def _atualizar_sidebar_dados(self) -> None:
        if not self._rl:
            return
        rl = self._rl
        self._lbl_dados["professores"].config(text=str(len(rl.professores)))
        self._lbl_dados["disciplinas"].config(text=str(len(rl.disciplinas)))
        self._lbl_dados["salas"].config(text=str(len(rl.salas)))
        self._lbl_dados["turmas"].config(text=str(len(rl.turmas)))

        n_inc = len(rl.inconsistencias)
        self._lbl_inc.config(
            text=str(n_inc),
            fg=CORES["erro"] if n_inc else CORES["sucesso"],
        )

    def _atualizar_sidebar_grade(self) -> None:
        if not self._rg:
            return
        rg = self._rg
        status = "COMPLETA" if rg.completa else "PARCIAL"
        self._var_grade_status.set(status)
        self._var_grade_blocos.set(
            f"{rg.total_blocos_alocados}/{rg.total_blocos_necessarios}"
        )
        self._var_grade_falhas.set(str(len(rg.falhas)))

    def _set_status(self, msg: str) -> None:
        self._var_status.set(msg)
        self.update_idletasks()
