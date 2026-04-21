"""
Teste do GeradorDeGrade com os dados de exemplo.
Execute: python -m tests.teste_gerador
"""

import sys
import io
import logging
from pathlib import Path

# Força UTF-8 no stdout para evitar UnicodeEncodeError no terminal Windows (cp1252)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from organizador_aulas.leitor_csv import LeitorCSV
from organizador_aulas.gerador import GeradorDeGrade

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(name)s | %(message)s",
)

ORDEM_DIAS = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado"]


def _sort_key_dia(dia: str) -> int:
    try:
        return ORDEM_DIAS.index(dia)
    except ValueError:
        return 99


def main() -> None:
    pasta_dados = Path(__file__).resolve().parent.parent / "dados"

    print(f"\n{'='*65}")
    print("  ETAPA 2 — Teste do GeradorDeGrade")
    print(f"{'='*65}\n")

    # --- 1. Leitura dos CSVs ---
    leitor = LeitorCSV(pasta_csv=pasta_dados)
    rl = leitor.carregar_tudo()

    if rl.inconsistencias:
        print("⚠️  Inconsistências nos CSVs:")
        for msg in rl.inconsistencias:
            print(f"  {msg}")
        print()

    # --- 2. Geração da grade ---
    gerador = GeradorDeGrade(
        resultado_leitura=rl,
        blocos_por_dia=8,
        max_iteracoes_backtrack=50_000,
        preferir_dias_distintos=True,
    )
    grade = gerador.gerar()

    # --- 3. Resumo geral ---
    print(grade.resumo())

    # --- 4. Avisos ---
    if grade.avisos:
        print(f"\n── AVISOS ({len(grade.avisos)}) " + "─" * 40)
        for msg in grade.avisos:
            print(f"  {msg}")

    # --- 5. Falhas ---
    if grade.falhas:
        print(f"\n── FALHAS DE ALOCAÇÃO ({len(grade.falhas)}) " + "─" * 30)
        for msg in grade.falhas:
            print(f"  {msg}")

    # --- 6. Grade por Turma ---
    print(f"\n{'='*65}")
    print("  GRADE POR TURMA")
    print(f"{'='*65}")
    for turma in rl.turmas.values():
        aulas = grade.aulas_por_turma(turma.id_turma)
        print(f"\n  📚 {turma.nome} — {turma.curso} ({turma.quantidade_alunos} alunos)")
        print(f"  {'Dia':<12} {'Bloco':>5}  {'Horário':<12} {'Disciplina':<35} {'Professor':<22} {'Sala'}")
        print(f"  {'-'*110}")
        if not aulas:
            print("    (nenhuma aula alocada)")
        for aula in sorted(aulas, key=lambda a: (_sort_key_dia(a.horario.dia), a.horario.numero_bloco)):
            print(
                f"  {aula.horario.dia:<12} {aula.horario.numero_bloco:>5}  "
                f"{aula.horario.hora_inicio}–{aula.horario.hora_fim}  "
                f"{aula.disciplina.nome:<35} {aula.professor.nome:<22} {aula.sala.numero}"
            )

    # --- 7. Grade por Professor ---
    print(f"\n{'='*65}")
    print("  GRADE POR PROFESSOR")
    print(f"{'='*65}")
    for prof in rl.professores.values():
        aulas = grade.aulas_por_professor(prof.id_professor)
        if not aulas:
            continue
        print(f"\n  👩‍🏫 {prof.nome} (dias: {', '.join(prof.dias_disponiveis)})")
        print(f"  {'Dia':<12} {'Bloco':>5}  {'Horário':<12} {'Turma':<18} {'Disciplina':<35} {'Sala'}")
        print(f"  {'-'*110}")
        for aula in sorted(aulas, key=lambda a: (_sort_key_dia(a.horario.dia), a.horario.numero_bloco)):
            print(
                f"  {aula.horario.dia:<12} {aula.horario.numero_bloco:>5}  "
                f"{aula.horario.hora_inicio}–{aula.horario.hora_fim}  "
                f"{aula.turma.nome:<18} {aula.disciplina.nome:<35} {aula.sala.numero}"
            )

    # --- 8. Exportação para CSV ---
    df = grade.to_dataframe()
    if not df.empty:
        saida_csv = pasta_dados.parent / "grade_gerada.csv"
        df.to_csv(saida_csv, index=False, encoding="utf-8-sig")
        print(f"\n✅ Grade exportada para: {saida_csv}")

    print(f"\n{'='*65}")
    print(f"  {'Geração CONCLUÍDA com sucesso.' if grade.completa else 'Geração PARCIAL — revise as falhas.'}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
