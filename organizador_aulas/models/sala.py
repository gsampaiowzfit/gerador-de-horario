"""
Modelo de entidade: Sala

Representa um espaço físico de aula com número identificador e capacidade máxima.
A capacidade é comparada ao número de alunos da turma durante a alocação.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Sala:
    """
    Entidade Sala.

    Atributos
    ----------
    id_sala : int
        Identificador único lido do CSV.
    numero : str
        Código/número da sala (ex: 'A101', '203', 'Lab de Informática').
        Armazenado como string para suportar formatos alfanuméricos.
    capacidade : int
        Número máximo de alunos que a sala comporta.

    Regra de negócio
    ----------------
    Uma sala só pode ser alocada para uma turma cujo número de alunos
    seja estritamente menor ou igual à sua capacidade.
    """

    id_sala: int
    numero: str
    capacidade: int

    def __post_init__(self) -> None:
        if self.capacidade < 1:
            raise ValueError(
                f"Sala '{self.numero}' tem capacidade inválida: {self.capacidade}. "
                "Deve ser >= 1."
            )

    # ------------------------------------------------------------------
    # Helpers de negócio
    # ------------------------------------------------------------------

    def comporta_turma(self, quantidade_alunos: int) -> bool:
        """
        Verifica se a sala tem capacidade para alocar a turma.

        Parâmetros
        ----------
        quantidade_alunos : int
            Número de alunos matriculados na turma a ser alocada.

        Retorno
        -------
        bool
            True se capacidade >= quantidade_alunos.
        """
        return self.capacidade >= quantidade_alunos

    # ------------------------------------------------------------------
    # Representações
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Sala(id={self.id_sala}, numero='{self.numero}', "
            f"capacidade={self.capacidade})"
        )

    def __str__(self) -> str:
        return f"Sala {self.numero} (cap. {self.capacidade} alunos, ID: {self.id_sala})"
