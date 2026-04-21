"""
Modelo de entidade: Turma

Representa um grupo de alunos vinculado a um curso e a um conjunto de disciplinas.
Os IDs das disciplinas são armazenados como lista de inteiros (já parseados pelo
LeitorCSV a partir do formato 'id1;id2;id3' do CSV).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class Turma:
    """
    Entidade Turma.

    Atributos
    ----------
    id_turma : int
        Identificador único lido do CSV.
    nome : str
        Nome ou código da turma (ex: 'Turma A', '2024-ADS-N1').
    curso : str
        Nome do curso ao qual a turma pertence.
    id_disciplinas : List[int]
        Lista de IDs das disciplinas que a turma cursa.
        Originalmente armazenada no CSV como '101;102;103'.
    quantidade_alunos : int
        Número de alunos matriculados — usado para validar capacidade de sala.

    Regras de negócio
    -----------------
    - Uma turma não pode ter mais de uma aula no mesmo horário (conflito de turma).
    - A sala alocada deve comportar todos os alunos da turma.
    """

    id_turma: int
    nome: str
    curso: str
    id_disciplinas: List[int] = field(default_factory=list)
    quantidade_alunos: int = 0

    def __post_init__(self) -> None:
        if self.quantidade_alunos < 0:
            raise ValueError(
                f"Turma '{self.nome}' tem quantidade_alunos negativa: "
                f"{self.quantidade_alunos}."
            )

    # ------------------------------------------------------------------
    # Helpers de negócio
    # ------------------------------------------------------------------

    def possui_disciplina(self, id_disciplina: int) -> bool:
        """Verifica se esta turma está matriculada na disciplina informada."""
        return id_disciplina in self.id_disciplinas

    @property
    def total_disciplinas(self) -> int:
        """Quantidade de disciplinas que a turma cursa."""
        return len(self.id_disciplinas)

    # ------------------------------------------------------------------
    # Representações
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        discs = self.id_disciplinas or []
        return (
            f"Turma(id={self.id_turma}, nome='{self.nome}', curso='{self.curso}', "
            f"alunos={self.quantidade_alunos}, disciplinas={discs})"
        )

    def __str__(self) -> str:
        return (
            f"{self.nome} — {self.curso} "
            f"({self.quantidade_alunos} alunos, {self.total_disciplinas} disciplinas, "
            f"ID: {self.id_turma})"
        )
