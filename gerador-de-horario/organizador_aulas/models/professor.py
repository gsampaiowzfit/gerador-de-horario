"""
Modelo de entidade: Professor

Representa um docente com suas disponibilidades semanais.
Os dias disponíveis são armazenados como uma lista normalizada de strings
(ex: ['Segunda', 'Quarta', 'Sexta']) para comparação direta com os slots
de horário durante a geração de grade.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


# Mapeamento canônico de dias para garantir consistência na comparação
DIAS_SEMANA_VALIDOS = [
    "Segunda",
    "Terca",
    "Quarta",
    "Quinta",
    "Sexta",
    "Sabado",
]

# Variações aceitas → forma canônica (normalização de entrada do CSV)
_ALIAS_DIAS: dict[str, str] = {
    "segunda": "Segunda",
    "segunda-feira": "Segunda",
    "seg": "Segunda",
    "terca": "Terca",
    "terça": "Terca",
    "terca-feira": "Terca",
    "terça-feira": "Terca",
    "ter": "Terca",
    "quarta": "Quarta",
    "quarta-feira": "Quarta",
    "qua": "Quarta",
    "quinta": "Quinta",
    "quinta-feira": "Quinta",
    "qui": "Quinta",
    "sexta": "Sexta",
    "sexta-feira": "Sexta",
    "sex": "Sexta",
    "sabado": "Sabado",
    "sábado": "Sabado",
    "sab": "Sabado",
}


def normalizar_dia(dia: str) -> str:
    """
    Converte qualquer variação textual de dia para a forma canônica.
    Levanta ValueError se o dia não for reconhecido.
    """
    chave = dia.strip().lower()
    if chave not in _ALIAS_DIAS:
        raise ValueError(
            f"Dia '{dia}' não reconhecido. "
            f"Valores aceitos (variações incluídas): {list(_ALIAS_DIAS.keys())}"
        )
    return _ALIAS_DIAS[chave]


@dataclass
class Professor:
    """
    Entidade Professor.

    Atributos
    ----------
    id_professor : int
        Identificador único lido do CSV.
    nome : str
        Nome completo do professor.
    dias_disponiveis : List[str]
        Lista de dias canônicos em que o professor está disponível
        (ex: ['Segunda', 'Quarta']).

    Propriedades calculadas
    -----------------------
    quantidade_dias_disponiveis : int
        Número de dias disponíveis — usado pelo GeradorDeGrade para
        ordenar a prioridade de alocação (professores com menos dias
        disponíveis devem ser alocados primeiro).
    esta_disponivel_em : Callable
        Verifica se o professor está disponível em determinado dia.
    """

    id_professor: int
    nome: str
    dias_disponiveis: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Garante que os dias já foram normalizados antes de armazenar
        self.dias_disponiveis = [normalizar_dia(d) for d in self.dias_disponiveis]

    # ------------------------------------------------------------------
    # Propriedades e helpers
    # ------------------------------------------------------------------

    @property
    def quantidade_dias_disponiveis(self) -> int:
        """Número de dias disponíveis (usado como critério de prioridade)."""
        return len(self.dias_disponiveis)

    def esta_disponivel_em(self, dia: str) -> bool:
        """
        Verifica se o professor leciona no dia fornecido.

        Parâmetros
        ----------
        dia : str
            Dia na forma canônica ou como alias (a normalização é aplicada).
        """
        try:
            dia_normalizado = normalizar_dia(dia)
        except ValueError:
            return False
        return dia_normalizado in self.dias_disponiveis

    # ------------------------------------------------------------------
    # Representações
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        dias = ", ".join(self.dias_disponiveis) if self.dias_disponiveis else "nenhum"
        return (
            f"Professor(id={self.id_professor}, nome='{self.nome}', "
            f"dias_disponiveis=[{dias}])"
        )

    def __str__(self) -> str:
        return f"{self.nome} (ID: {self.id_professor})"
