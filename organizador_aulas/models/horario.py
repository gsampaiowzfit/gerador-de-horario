"""
Modelo de entidade: Horario

Representa um slot de tempo na grade semanal, identificado por dia da semana
e número de bloco. Cada bloco tem duração fixa de 50 minutos.

Esta classe é *imutável* (frozen=True) e *hashável*, podendo ser usada
diretamente como chave em dicionários e como elemento de conjuntos —
requisito essencial para os registros de ocupação do algoritmo GeradorDeGrade.

Configuração de tempo
---------------------
Os horários de início/fim são calculados a partir de `HORA_INICIO_PADRAO`
com o offset de cada bloco. Intervalos entre blocos também são configuráveis.
Estes atributos de classe podem ser alterados antes de instanciar qualquer
Horario se a instituição tiver um calendário diferente do padrão (07:00).

Exemplo de blocos com HORA_INICIO_PADRAO = (7, 0) e INTERVALO = 10 min:
  Bloco 1 → 07:00 – 07:50
  Bloco 2 → 08:00 – 08:50
  Bloco 3 → 09:00 – 09:50
  ...
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Tuple


@dataclass(frozen=True)
class Horario:
    """
    Entidade Horario — um slot de tempo único na grade semanal.

    Atributos
    ----------
    dia : str
        Dia da semana na forma canônica (ex: 'Segunda', 'Terca').
    numero_bloco : int
        Número do bloco no dia, a partir de 1 (ex: 1 = primeiro horário do dia).

    Propriedades calculadas
    -----------------------
    hora_inicio : str   ex: '07:00'
    hora_fim    : str   ex: '07:50'
    """

    dia: str
    numero_bloco: int  # 1-based

    # ------------------------------------------------------------------
    # Configurações de tempo (atributos de classe modificáveis)
    # ------------------------------------------------------------------
    DURACAO_BLOCO_MIN: ClassVar[int] = 50
    INTERVALO_CURTO_MIN: ClassVar[int] = 0
    INTERVALO_LONGO_MIN: ClassVar[int] = 20
    
    HORA_INICIO_MANHA: ClassVar[Tuple[int, int]] = (8, 0)
    HORA_INICIO_NOITE: ClassVar[Tuple[int, int]] = (19, 0)

    # ------------------------------------------------------------------
    # Validação pós-construção
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        if self.numero_bloco < 1 or self.numero_bloco > 8:
            raise ValueError(
                f"numero_bloco deve estar entre 1 e 8, recebido: {self.numero_bloco}"
            )
        if not self.dia or not self.dia.strip():
            raise ValueError("dia não pode ser vazio.")

    # ------------------------------------------------------------------
    # Cálculo de horários
    # ------------------------------------------------------------------

    @property
    def _inicio_em_minutos(self) -> int:
        """Minutos desde meia-noite para o início deste bloco."""
        # Blocos 1-4: Manhã (Base 08:00)
        # Blocos 5-8: Noite (Base 19:00)
        
        if self.numero_bloco <= 4:
            h, m = self.HORA_INICIO_MANHA
            bloco_relativo = self.numero_bloco
        else:
            h, m = self.HORA_INICIO_NOITE
            bloco_relativo = self.numero_bloco - 4
            
        base = h * 60 + m
        
        # Cálculo do offset:
        # Bloco 1: 0
        # Bloco 2: 50
        # Bloco 3: 50 + 50 + 20 (intervalo) = 120
        # Bloco 4: 120 + 50 = 170
        
        offset = 0
        if bloco_relativo >= 2:
            offset += 50  # Bloco 1
        if bloco_relativo >= 3:
            offset += 50 + self.INTERVALO_LONGO_MIN  # Bloco 2 + intervalo
        if bloco_relativo >= 4:
            offset += 50  # Bloco 3
            
        return base + offset

    @property
    def hora_inicio(self) -> str:
        """Hora de início no formato HH:MM."""
        h, m = divmod(self._inicio_em_minutos, 60)
        return f"{h:02d}:{m:02d}"

    @property
    def hora_fim(self) -> str:
        """Hora de término no formato HH:MM."""
        fim = self._inicio_em_minutos + self.DURACAO_BLOCO_MIN
        h, m = divmod(fim, 60)
        return f"{h:02d}:{m:02d}"

    # ------------------------------------------------------------------
    # Representações
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        periodo = "Manhã" if self.numero_bloco <= 4 else "Noite"
        bloco_exibicao = self.numero_bloco if self.numero_bloco <= 4 else self.numero_bloco - 4
        return f"{self.dia} | {periodo} - Bloco {bloco_exibicao} ({self.hora_inicio}–{self.hora_fim})"

    def __repr__(self) -> str:
        return (
            f"Horario(dia='{self.dia}', bloco={self.numero_bloco}, "
            f"{self.hora_inicio}–{self.hora_fim})"
        )
