"""
Script de smoke test para validar o LeitorCSV com os dados de exemplo.
Execute: python -m tests.teste_leitor
"""

import sys
import logging
from pathlib import Path

# Garante que o root do projeto está no sys.path quando executado direto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from organizador_aulas.leitor_csv import LeitorCSV

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)-8s | %(name)s | %(message)s",
)


def main() -> None:
    pasta_dados = Path(__file__).resolve().parent.parent / "dados"
    print(f"\n{'='*60}")
    print(f"  Teste do LeitorCSV — pasta: {pasta_dados}")
    print(f"{'='*60}\n")

    leitor = LeitorCSV(pasta_csv=pasta_dados)
    resultado = leitor.carregar_tudo()

    # --- Resumo ---
    print(resultado.resumo())
    print()

    # --- Entidades carregadas ---
    print("── PROFESSORES ─────────────────────────────────────────")
    for prof in resultado.professores.values():
        print(f"  {prof}")

    print("\n── DISCIPLINAS ──────────────────────────────────────────")
    for disc in resultado.disciplinas.values():
        print(f"  {disc}")

    print("\n── SALAS ────────────────────────────────────────────────")
    for sala in resultado.salas.values():
        print(f"  {sala}")

    print("\n── TURMAS ───────────────────────────────────────────────")
    for turma in resultado.turmas.values():
        print(f"  {turma}")

    # --- Inconsistências ---
    if resultado.inconsistencias:
        print(f"\n── INCONSISTÊNCIAS ({len(resultado.inconsistencias)}) ──────────────────────")
        for msg in resultado.inconsistencias:
            print(f"  {msg}")
    else:
        print("\n✅ Nenhuma inconsistência detectada.")

    print(f"\n{'='*60}")
    print(f"  Sucesso: {resultado.sucesso}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
