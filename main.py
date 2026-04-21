"""
main.py — Ponto de entrada do Organizador de Aulas.

Execute:
    python main.py
"""

import sys
from pathlib import Path

# Garante que o pacote organizador_aulas seja encontrado
sys.path.insert(0, str(Path(__file__).resolve().parent))

from organizador_aulas.gui.app import App

if __name__ == "__main__":
    app = App()
    app.mainloop()
