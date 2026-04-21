"""
dialogo_carregar.py — Diálogos modais da aplicação.

DialogoCarregarCSV    Seleciona os 4 arquivos CSV individualmente ou por pasta.
DialogoConfiguracoes  Ajusta parâmetros de geração (blocos/dia, dias, max_iter).
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Dict, Optional

from organizador_aulas.gui.estilos import CORES, FONTES


# ── Helpers ───────────────────────────────────────────────────────────────────

def _centralizar(janela: tk.Toplevel, parent: tk.Widget) -> None:
    janela.update_idletasks()
    px = parent.winfo_rootx() + parent.winfo_width() // 2
    py = parent.winfo_rooty() + parent.winfo_height() // 2
    w, h = janela.winfo_reqwidth(), janela.winfo_reqheight()
    janela.geometry(f"+{px - w // 2}+{py - h // 2}")


def _header_dialogo(parent: tk.Toplevel, titulo: str, subtitulo: str) -> None:
    hdr = tk.Frame(parent, bg=CORES["bg_header"], pady=16)
    hdr.pack(fill=tk.X)
    tk.Label(hdr, text=titulo, bg=CORES["bg_header"], fg="white",
             font=FONTES["titulo"]).pack(padx=24)
    tk.Label(hdr, text=subtitulo, bg=CORES["bg_header"],
             fg=CORES["texto_sidebar"], font=FONTES["pequena"]).pack()


def _rodape_dialogo(parent: tk.Toplevel, cmd_ok, cmd_cancel,
                    txt_ok: str = "✔  Confirmar") -> None:
    tk.Frame(parent, bg=CORES["borda"], height=1).pack(fill=tk.X)
    rod = tk.Frame(parent, bg=CORES["bg_app"], padx=20, pady=14)
    rod.pack(fill=tk.X)
    tk.Button(rod, text="  Cancelar  ", font=FONTES["corpo"],
              bg=CORES["bg_card"], fg=CORES["texto_secundario"],
              bd=1, relief="solid", cursor="hand2", pady=5,
              command=cmd_cancel).pack(side=tk.RIGHT, padx=(8, 0))
    tk.Button(rod, text=f"  {txt_ok}  ", font=FONTES["btn"],
              bg=CORES["accent"], fg="white", bd=0,
              cursor="hand2", pady=5,
              command=cmd_ok).pack(side=tk.RIGHT)


# ── DialogoCarregarCSV ────────────────────────────────────────────────────────

class DialogoCarregarCSV(tk.Toplevel):
    """
    Janela modal para selecionar os 4 arquivos CSV.

    Após fechar, `self.resultado` contém {chave: path} dos arquivos selecionados
    ou None se o usuário cancelou.
    """

    _ARQUIVOS = [
        ("professores", "Professores.csv", "👨‍🏫  Professores"),
        ("disciplinas", "Disciplinas.csv", "📖  Disciplinas"),
        ("turmas",      "Turmas.csv",      "👥  Turmas"),
        ("salas",       "Salas.csv",       "🏫  Salas"),
    ]

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.resultado: Optional[Dict[str, str]] = None
        self.title("Carregar Arquivos CSV")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=CORES["bg_card"])

        self._vars: Dict[str, tk.StringVar] = {
            k: tk.StringVar() for k, _, _ in self._ARQUIVOS
        }
        self._construir()
        _centralizar(self, parent)

    def _construir(self) -> None:
        _header_dialogo(
            self,
            "📂  Carregar Arquivos CSV",
            "Selecione cada arquivo individualmente ou use 'Carregar Pasta'.",
        )

        corpo = tk.Frame(self, bg=CORES["bg_card"], padx=28, pady=20)
        corpo.pack(fill=tk.BOTH)

        # Botão de pasta
        tk.Button(
            corpo,
            text="📁  Carregar pasta completa (auto-detecta nomes padrão)",
            font=FONTES["corpo"], bg=CORES["accent_light"],
            fg=CORES["accent"], bd=0, cursor="hand2",
            padx=12, pady=6, command=self._carregar_pasta,
        ).pack(anchor="w", pady=(0, 14))

        ttk.Separator(corpo, orient="horizontal").pack(fill=tk.X, pady=(0, 14))

        # Linhas de arquivo
        for chave, _, label_txt in self._ARQUIVOS:
            self._linha_arquivo(corpo, chave, label_txt)

        _rodape_dialogo(self, self._confirmar, self.destroy, "Carregar")

    def _linha_arquivo(self, parent: tk.Frame, chave: str, label_txt: str) -> None:
        row = tk.Frame(parent, bg=CORES["bg_card"])
        row.pack(fill=tk.X, pady=4)

        tk.Label(
            row, text=label_txt, font=FONTES["corpo_bold"],
            bg=CORES["bg_card"], fg=CORES["texto_primario"],
            width=18, anchor="w",
        ).pack(side=tk.LEFT)

        tk.Entry(
            row, textvariable=self._vars[chave],
            font=FONTES["pequena"], bg=CORES["bg_app"],
            fg=CORES["texto_primario"], relief="solid", bd=1, width=38,
        ).pack(side=tk.LEFT, padx=(8, 4), ipady=4)

        tk.Button(
            row, text="📂", font=FONTES["corpo"],
            bg=CORES["bg_card"], fg=CORES["accent"], bd=0, cursor="hand2",
            command=lambda k=chave: self._selecionar_arquivo(k),
        ).pack(side=tk.LEFT)

    def _selecionar_arquivo(self, chave: str) -> None:
        path = filedialog.askopenfilename(
            title=f"Selecionar {chave}.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self._vars[chave].set(path)

    def _carregar_pasta(self) -> None:
        pasta = filedialog.askdirectory(title="Selecionar pasta com os CSVs")
        if not pasta:
            return
        pasta_p = Path(pasta)
        for chave, nome_padrao, _ in self._ARQUIVOS:
            candidato = pasta_p / nome_padrao
            if candidato.exists():
                self._vars[chave].set(str(candidato))

    def _confirmar(self) -> None:
        paths = {k: v.get().strip() for k, v in self._vars.items()}
        preenchidos = {k: v for k, v in paths.items() if v}
        if not preenchidos:
            tk.messagebox.showwarning(
                "Atenção",
                "Selecione ao menos um arquivo CSV.",
                parent=self,
            )
            return
        self.resultado = preenchidos
        self.destroy()


# ── DialogoConfiguracoes ──────────────────────────────────────────────────────

class DialogoConfiguracoes(tk.Toplevel):
    """
    Diálogo modal de configurações de geração da grade.

    Permite ajustar:
    - Número de blocos por dia
    - Dias letivos considerados
    - Limite de iterações do backtracking
    """

    _DIAS_OPCOES = [
        ("Segunda",  "Segunda-feira"),
        ("Terca",    "Terça-feira"),
        ("Quarta",   "Quarta-feira"),
        ("Quinta",   "Quinta-feira"),
        ("Sexta",    "Sexta-feira"),
        ("Sabado",   "Sábado"),
    ]

    def __init__(
        self,
        parent: tk.Widget,
        var_blocos: tk.IntVar,
        var_max_iter: tk.IntVar,
        vars_dias: Dict[str, tk.BooleanVar],
    ) -> None:
        super().__init__(parent)
        self.title("Configurações de Geração")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=CORES["bg_card"])

        self._var_blocos = var_blocos
        self._var_max_iter = var_max_iter
        self._vars_dias = vars_dias

        self._construir()
        _centralizar(self, parent)

    def _construir(self) -> None:
        _header_dialogo(
            self,
            "⚙️  Configurações de Geração",
            "Ajuste os parâmetros do algoritmo de geração de grade.",
        )

        corpo = tk.Frame(self, bg=CORES["bg_card"], padx=28, pady=20)
        corpo.pack(fill=tk.BOTH)

        # Blocos por dia
        sec = self._secao(corpo, "Blocos de 50 min por dia")
        row_b = tk.Frame(sec, bg=CORES["bg_card"])
        row_b.pack(anchor="w", pady=(0, 4))
        tk.Label(row_b, text="Quantidade de blocos:",
                 font=FONTES["corpo"], bg=CORES["bg_card"],
                 fg=CORES["texto_primario"]).pack(side=tk.LEFT)
        ttk.Spinbox(
            row_b,
            from_=1, to=16, width=5,
            textvariable=self._var_blocos,
            font=FONTES["corpo"],
        ).pack(side=tk.LEFT, padx=8)
        tk.Label(row_b, text="blocos  (máx. 16 × 50 min = 800 min/dia)",
                 font=FONTES["pequena"], bg=CORES["bg_card"],
                 fg=CORES["texto_secundario"]).pack(side=tk.LEFT)

        # Dias letivos
        sec2 = self._secao(corpo, "Dias letivos considerados")
        dias_frame = tk.Frame(sec2, bg=CORES["bg_card"])
        dias_frame.pack(anchor="w")
        for i, (chave, label) in enumerate(self._DIAS_OPCOES):
            tk.Checkbutton(
                dias_frame, text=label, variable=self._vars_dias[chave],
                font=FONTES["corpo"], bg=CORES["bg_card"],
                fg=CORES["texto_primario"],
                activebackground=CORES["bg_card"],
                selectcolor=CORES["accent_light"],
            ).grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 20), pady=2)

        # Limite de iterações
        sec3 = self._secao(corpo, "Algoritmo de Backtracking")
        row_it = tk.Frame(sec3, bg=CORES["bg_card"])
        row_it.pack(anchor="w")
        tk.Label(row_it, text="Máx. iterações:",
                 font=FONTES["corpo"], bg=CORES["bg_card"],
                 fg=CORES["texto_primario"]).pack(side=tk.LEFT)
        ttk.Spinbox(
            row_it,
            from_=1_000, to=500_000, increment=5_000, width=10,
            textvariable=self._var_max_iter,
            font=FONTES["corpo"],
        ).pack(side=tk.LEFT, padx=8)
        tk.Label(row_it, text="(use valores maiores para grades mais complexas)",
                 font=FONTES["pequena"], bg=CORES["bg_card"],
                 fg=CORES["texto_secundario"]).pack(side=tk.LEFT)

        _rodape_dialogo(self, self.destroy, self.destroy, "Salvar e Fechar")

    @staticmethod
    def _secao(parent: tk.Frame, titulo: str) -> tk.Frame:
        tk.Label(parent, text=titulo, font=FONTES["corpo_bold"],
                 bg=CORES["bg_card"], fg=CORES["texto_primario"]).pack(
            anchor="w", pady=(12, 4)
        )
        frame = tk.Frame(parent, bg=CORES["bg_card"])
        frame.pack(fill=tk.X, padx=8)
        return frame
