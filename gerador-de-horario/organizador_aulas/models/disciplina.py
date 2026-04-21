"""
Modelo de entidade: Disciplina

Representa uma matéria/componente curricular com sua carga horária expressa
em blocos de 50 minutos. Opcionalmente vinculada a um professor responsável.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Disciplina:
    """
    Entidade Disciplina.

    Atributos
    ----------
    id_disciplina : int
        Identificador único lido do CSV.
    nome : str
        Nome da disciplina (ex: 'Cálculo I', 'Programação Orientada a Objetos').
    carga_horaria_semanal : int
        Número de blocos de 50 minutos que devem ser alocados por semana.
        Exemplo: 4 blocos = 4 × 50 min = 200 min semanais.
    id_professor : Optional[int]
        ID do professor responsável pela disciplina.
        Pode ser None se ainda não associado (o LeitorCSV trata este campo
        alternativamente via coluna id_professor em Professores_Disciplinas.csv
        dependendo do esquema adotado).

    Propriedades calculadas
    -----------------------
    carga_horaria_minutos : int
        Carga horária total em minutos (blocos × 50).
    """

    id_disciplina: int
    nome: str
    carga_horaria_semanal: int  # em blocos de 50 min
    id_professor: Optional[int] = None

    def __post_init__(self) -> None:
        if self.carga_horaria_semanal < 1:
            raise ValueError(
                f"Disciplina '{self.nome}' tem carga_horaria_semanal inválida: "
                f"{self.carga_horaria_semanal}. Deve ser >= 1 bloco."
            )

    # ------------------------------------------------------------------
    # Propriedades calculadas
    # ------------------------------------------------------------------

    @property
    def carga_horaria_minutos(self) -> int:
        """Carga horária total semanal em minutos."""
        return self.carga_horaria_semanal * 50

    # ------------------------------------------------------------------
    # Representações
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        professor_info = (
            f"id_professor={self.id_professor}" if self.id_professor else "sem professor"
        )
        return (
            f"Disciplina(id={self.id_disciplina}, nome='{self.nome}', "
            f"blocos_semanais={self.carga_horaria_semanal}, {professor_info})"
        )

    def __str__(self) -> str:
        return f"{self.nome} (ID: {self.id_disciplina}, {self.carga_horaria_semanal} blocos/sem)"
