"""
Modelo de entidade: Aula

Representa uma aula efetivamente alocada na grade horária.
Liga as cinco entidades de domínio: Disciplina, Professor, Turma, Sala e Horario.

Cada instância de Aula é o resultado de uma decisão do GeradorDeGrade e
representa um único bloco de 50 minutos já confirmado sem conflitos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .disciplina import Disciplina
from .horario import Horario
from .professor import Professor
from .sala import Sala
from .turma import Turma


@dataclass
class Aula:
    """
    Entidade Aula — bloco de 50 minutos alocado na grade sem conflitos.

    Atributos
    ----------
    id_aula : int
        Identificador sequencial gerado automaticamente pelo GeradorDeGrade.
    disciplina : Disciplina
        A disciplina sendo ministrada.
    professor : Professor
        O professor responsável por esta aula.
    turma : Turma
        A turma que assiste esta aula.
    sala : Sala
        A sala física onde a aula ocorre.
    horario : Horario
        O slot de tempo (dia + bloco) desta aula.

    Invariante
    ----------
    Uma instância válida de Aula garante que, no momento de sua criação pelo
    GeradorDeGrade, todas as restrições foram satisfeitas:
    - professor disponível no dia
    - professor / sala / turma sem conflito neste slot
    - sala com capacidade >= turma.quantidade_alunos
    """

    id_aula: int
    disciplina: Disciplina
    professor: Professor
    turma: Turma
    sala: Sala
    horario: Horario

    # ------------------------------------------------------------------
    # Helpers de verificação rápida
    # ------------------------------------------------------------------

    @property
    def slot(self) -> tuple[str, int]:
        """Retorna o slot como tupla (dia, numero_bloco) — chave usada internamente."""
        return (self.horario.dia, self.horario.numero_bloco)

    # ------------------------------------------------------------------
    # Serialização
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa a aula para dicionário (útil para criar DataFrames pandas
        e popular a interface gráfica).
        """
        return {
            "id_aula": self.id_aula,
            "dia": self.horario.dia,
            "bloco": self.horario.numero_bloco,
            "hora_inicio": self.horario.hora_inicio,
            "hora_fim": self.horario.hora_fim,
            "disciplina": self.disciplina.nome,
            "id_disciplina": self.disciplina.id_disciplina,
            "professor": self.professor.nome,
            "id_professor": self.professor.id_professor,
            "turma": self.turma.nome,
            "id_turma": self.turma.id_turma,
            "curso": self.turma.curso,
            "sala": self.sala.numero,
            "id_sala": self.sala.id_sala,
            "capacidade_sala": self.sala.capacidade,
            "alunos_turma": self.turma.quantidade_alunos,
        }

    # ------------------------------------------------------------------
    # Representações
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            f"[{self.horario}] {self.disciplina.nome} | "
            f"Turma: {self.turma.nome} | "
            f"Prof: {self.professor.nome} | "
            f"Sala: {self.sala.numero}"
        )

    def __repr__(self) -> str:
        return (
            f"Aula(id={self.id_aula}, "
            f"disc='{self.disciplina.nome}', "
            f"turma='{self.turma.nome}', "
            f"prof='{self.professor.nome}', "
            f"sala='{self.sala.numero}', "
            f"horario={self.horario!r})"
        )
