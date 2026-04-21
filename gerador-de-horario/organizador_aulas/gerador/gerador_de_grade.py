"""
GeradorDeGrade — Núcleo do sistema de geração automática de horários.

Algoritmo
---------
A geração segue a estratégia de **Backtracking com fallback guloso**:

  Fase 1 — Backtracking puro
    Cada bloco de 50 min a alocar é representado por uma Tarefa.
    As tarefas são ordenadas por prioridade (mais restritivas primeiro):
      • Professores com menos dias disponíveis (alocados antes).
      • Disciplinas com maior carga horária (mais blocos = mais difícil distribuir).
    O algoritmo navega a árvore de decisão: para cada tarefa, tenta todos os
    pares válidos (slot, sala). Se uma escolha impede alocações futuras, desfaz
    a decisão (undo O(1)) e tenta a próxima opção.

  Fase 2 — Passe Guloso (fallback)
    Se o backtracking atingir o limite de iterações (_BacktrackingTimeout), o
    estado parcial é preservado e um passe guloso simples preenche os blocos
    restantes sem backtrack. Falhas são registradas com diagnóstico detalhado.

Restrições verificadas
----------------------
  ✔ Professor não pode lecionar duas aulas no mesmo slot.
  ✔ Turma não pode ter mais de uma aula no mesmo slot.
  ✔ Sala não pode ser compartilhada no mesmo slot.
  ✔ Disponibilidade semanal do professor (dia da semana) é respeitada.
  ✔ Capacidade da sala >= quantidade de alunos da turma.
  ✔ Carga horária semanal de cada disciplina por turma é atendida.

Heurística extra
----------------
  Blocos da mesma (turma, disciplina) são preferencialmente distribuídos
  em dias diferentes, evitando duas aulas da mesma matéria no mesmo dia.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from organizador_aulas.leitor_csv import ResultadoLeitura
from organizador_aulas.models.aula import Aula
from organizador_aulas.models.horario import Horario
from organizador_aulas.models.professor import Professor
from organizador_aulas.models.disciplina import Disciplina
from organizador_aulas.models.turma import Turma
from organizador_aulas.models.sala import Sala

logger = logging.getLogger(__name__)

# Alias interno: (dia_canonico, numero_bloco)
Slot = Tuple[str, int]
# Chave de grupo: (id_turma, id_disciplina)
ChaveGrupo = Tuple[int, int]


# ---------------------------------------------------------------------------
# Exceção interna de timeout do backtracking
# ---------------------------------------------------------------------------


class _BacktrackingTimeout(Exception):
    """Levantada quando o limite de iterações do backtracking é atingido."""


# ---------------------------------------------------------------------------
# Tarefa interna — representa um único bloco a alocar
# ---------------------------------------------------------------------------


@dataclass
class Tarefa:
    """
    Representa UM bloco de 50 minutos a ser alocado para (turma, disciplina).

    Para uma disciplina com carga_horaria_semanal = 3, serão criadas
    3 instâncias de Tarefa para cada turma que a cursa, identificadas por
    numero_bloco_disc = 1, 2 e 3.
    """

    turma: Turma
    disciplina: Disciplina
    professor: Professor
    numero_bloco_disc: int  # qual bloco desta disciplina (1..N)

    @property
    def chave_grupo(self) -> ChaveGrupo:
        """(id_turma, id_disciplina) — identifica o grupo de tarefas."""
        return (self.turma.id_turma, self.disciplina.id_disciplina)

    @property
    def prioridade(self) -> Tuple[int, int]:
        """
        Chave de ordenação para alocação mais restritiva primeiro:
          (dias_disponiveis ASC, carga_horaria DESC, numero_bloco ASC)
        """
        return (
            self.professor.quantidade_dias_disponiveis,  # menos dias → mais urgente
            -self.disciplina.carga_horaria_semanal,       # mais blocos → mais urgente
            self.numero_bloco_disc,
        )


# ---------------------------------------------------------------------------
# Estado do backtracking — estrutura mutável com undo O(1)
# ---------------------------------------------------------------------------


@dataclass
class _EstadoBacktrack:
    """
    Rastreia os slots ocupados durante o backtracking.

    Todas as operações de alocação e desalocação são O(1) usando conjuntos,
    o que garante performance mesmo com muitos backtracks.
    """

    # Registros de ocupação: entidade_id → set de slots ocupados
    prof_ocupado: Dict[int, Set[Slot]] = field(default_factory=dict)
    sala_ocupada: Dict[int, Set[Slot]] = field(default_factory=dict)
    turma_ocupada: Dict[int, Set[Slot]] = field(default_factory=dict)

    # Dias já usados por (turma_id, disc_id) — para heurística de distribuição
    turma_disc_dias: Dict[ChaveGrupo, Set[str]] = field(default_factory=dict)

    # Lista de aulas alocadas com sucesso (resultado final)
    aulas: List[Aula] = field(default_factory=list)
    _proximo_id: int = field(default=1, init=False)

    # ------------------------------------------------------------------

    def alocar(self, tarefa: Tarefa, slot: Slot, sala: Sala) -> Aula:
        """
        Registra a alocação de uma tarefa em um slot/sala.
        Retorna o objeto Aula criado.
        """
        dia, bloco = slot
        aula = Aula(
            id_aula=self._proximo_id,
            disciplina=tarefa.disciplina,
            professor=tarefa.professor,
            turma=tarefa.turma,
            sala=sala,
            horario=Horario(dia=dia, numero_bloco=bloco),
        )
        self._proximo_id += 1

        id_prof = tarefa.professor.id_professor
        id_sala = sala.id_sala
        id_turma = tarefa.turma.id_turma
        chave = tarefa.chave_grupo

        self.prof_ocupado.setdefault(id_prof, set()).add(slot)
        self.sala_ocupada.setdefault(id_sala, set()).add(slot)
        self.turma_ocupada.setdefault(id_turma, set()).add(slot)
        self.turma_disc_dias.setdefault(chave, set()).add(dia)
        self.aulas.append(aula)

        return aula

    def desalocar(self, aula: Aula) -> None:
        """
        Desfaz a alocação de uma aula (undo para backtracking).
        Todas as remoções são O(1).
        """
        slot: Slot = (aula.horario.dia, aula.horario.numero_bloco)
        chave: ChaveGrupo = (aula.turma.id_turma, aula.disciplina.id_disciplina)

        self.prof_ocupado.get(aula.professor.id_professor, set()).discard(slot)
        self.sala_ocupada.get(aula.sala.id_sala, set()).discard(slot)
        self.turma_ocupada.get(aula.turma.id_turma, set()).discard(slot)

        # Remove dia do registro apenas se não há mais nenhuma aula nesse dia para o grupo
        if aula in self.aulas:
            self.aulas.remove(aula)

        # Recalcula dias do grupo a partir das aulas remanescentes
        dias_restantes = {
            a.horario.dia
            for a in self.aulas
            if a.turma.id_turma == aula.turma.id_turma
            and a.disciplina.id_disciplina == aula.disciplina.id_disciplina
        }
        self.turma_disc_dias[chave] = dias_restantes
        self._proximo_id -= 1

    # ------------------------------------------------------------------
    # Predicados de disponibilidade (O(1))
    # ------------------------------------------------------------------

    def professor_livre(self, id_prof: int, slot: Slot) -> bool:
        return slot not in self.prof_ocupado.get(id_prof, set())

    def sala_livre(self, id_sala: int, slot: Slot) -> bool:
        return slot not in self.sala_ocupada.get(id_sala, set())

    def turma_livre(self, id_turma: int, slot: Slot) -> bool:
        return slot not in self.turma_ocupada.get(id_turma, set())

    def dias_usados_pelo_grupo(self, chave: ChaveGrupo) -> Set[str]:
        """Dias já usados por esta (turma, disciplina) para a heurística de distribuição."""
        return self.turma_disc_dias.get(chave, set())

    def blocos_alocados_do_grupo(self, chave: ChaveGrupo) -> int:
        """Quantos blocos desta (turma, disciplina) já foram alocados."""
        id_turma, id_disc = chave
        return sum(
            1
            for a in self.aulas
            if a.turma.id_turma == id_turma and a.disciplina.id_disciplina == id_disc
        )


# ---------------------------------------------------------------------------
# Resultado da geração
# ---------------------------------------------------------------------------


@dataclass
class ResultadoGrade:
    """
    Encapsula o resultado completo da geração de grade.

    Atributos
    ----------
    aulas : List[Aula]
        Todas as aulas alocadas sem conflitos.
    falhas : List[str]
        Mensagens detalhadas de cada bloco não alocado, incluindo
        diagnóstico da causa específica.
    avisos : List[str]
        Informações não-criticas sobre o processo de geração.
    completa : bool
        True se TODOS os blocos exigidos foram alocados com sucesso.
    total_blocos_necessarios : int
    total_blocos_alocados : int
    """

    aulas: List[Aula] = field(default_factory=list)
    falhas: List[str] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)
    completa: bool = True
    total_blocos_necessarios: int = 0
    total_blocos_alocados: int = 0

    # ------------------------------------------------------------------
    # Consultas por entidade
    # ------------------------------------------------------------------

    def aulas_por_turma(self, id_turma: int) -> List[Aula]:
        """Retorna as aulas de uma turma ordenadas por dia e bloco."""
        return sorted(
            [a for a in self.aulas if a.turma.id_turma == id_turma],
            key=lambda a: (a.horario.dia, a.horario.numero_bloco),
        )

    def aulas_por_professor(self, id_professor: int) -> List[Aula]:
        """Retorna as aulas de um professor ordenadas por dia e bloco."""
        return sorted(
            [a for a in self.aulas if a.professor.id_professor == id_professor],
            key=lambda a: (a.horario.dia, a.horario.numero_bloco),
        )

    def aulas_por_sala(self, id_sala: int) -> List[Aula]:
        """Retorna as aulas de uma sala ordenadas por dia e bloco."""
        return sorted(
            [a for a in self.aulas if a.sala.id_sala == id_sala],
            key=lambda a: (a.horario.dia, a.horario.numero_bloco),
        )

    # ------------------------------------------------------------------
    # Exportação
    # ------------------------------------------------------------------

    def to_dataframe(self):
        """
        Converte todas as aulas para um DataFrame pandas.
        Retorna DataFrame vazio se não houver aulas.
        """
        import pandas as pd

        if not self.aulas:
            return pd.DataFrame()
        return pd.DataFrame([a.to_dict() for a in self.aulas])

    # ------------------------------------------------------------------
    # Resumo textual
    # ------------------------------------------------------------------

    def resumo(self) -> str:
        status = "✅ COMPLETA" if self.completa else "⚠️  PARCIAL"
        linhas = [
            f"Status                : {status}",
            f"Blocos necessários    : {self.total_blocos_necessarios}",
            f"Blocos alocados       : {self.total_blocos_alocados}",
            f"Aulas geradas         : {len(self.aulas)}",
            f"Falhas de alocação    : {len(self.falhas)}",
            f"Avisos                : {len(self.avisos)}",
        ]
        return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Gerador principal
# ---------------------------------------------------------------------------


class GeradorDeGrade:
    """
    Gera automaticamente a grade horária semanal sem conflitos.

    Parâmetros
    ----------
    resultado_leitura : ResultadoLeitura
        Dados carregados e validados pelo LeitorCSV.
    dias_letivos : List[str] | None
        Dias a considerar. Padrão: ['Segunda','Terca','Quarta','Quinta','Sexta'].
    blocos_por_dia : int
        Quantidade de blocos de 50 min disponíveis por dia. Padrão: 8.
    max_iteracoes_backtrack : int
        Limite de iterações do backtracking para evitar timeout. Padrão: 50 000.
    preferir_dias_distintos : bool
        Se True, tenta alocar blocos da mesma (turma, disciplina) em dias
        diferentes (heurística de distribuição). Padrão: True.
    """

    DIAS_LETIVOS_PADRAO: List[str] = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta"]
    BLOCOS_POR_DIA_PADRAO: int = 8
    MAX_ITERACOES_PADRAO: int = 50_000

    def __init__(
        self,
        resultado_leitura: ResultadoLeitura,
        dias_letivos: Optional[List[str]] = None,
        blocos_por_dia: int = BLOCOS_POR_DIA_PADRAO,
        max_iteracoes_backtrack: int = MAX_ITERACOES_PADRAO,
        preferir_dias_distintos: bool = True,
    ) -> None:
        self._rl = resultado_leitura
        self._dias = dias_letivos or list(self.DIAS_LETIVOS_PADRAO)
        self._blocos_por_dia = blocos_por_dia
        self._max_iter = max_iteracoes_backtrack
        self._preferir_dias_distintos = preferir_dias_distintos

        # Todos os slots semanais: [(dia, bloco), ...]
        self._todos_slots: List[Slot] = [
            (dia, bloco)
            for dia in self._dias
            for bloco in range(1, blocos_por_dia + 1)
        ]

        # Salas ordenadas por capacidade decrescente (heurísica: maiores primeiro)
        self._salas: List[Sala] = sorted(
            resultado_leitura.salas.values(),
            key=lambda s: s.capacidade,
            reverse=True,
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def gerar(self) -> ResultadoGrade:
        """
        Executa a geração da grade e retorna o ResultadoGrade.

        Fluxo:
        1. Validações de pré-condição.
        2. Construção e ordenamento de tarefas por prioridade.
        3. Backtracking recursivo com proteção por limite de iterações.
        4. Se timeout → preserva estado parcial e executa passe guloso.
        5. Popula e retorna ResultadoGrade com aulas, falhas e avisos.
        """
        resultado = ResultadoGrade()

        # Etapa 1 — pré-validação
        if not self._validar_pre_geracao(resultado):
            resultado.completa = False
            return resultado

        # Etapa 2 — construção e ordenamento das tarefas
        tarefas = self._construir_tarefas(resultado)
        if not tarefas:
            resultado.avisos.append(
                "Nenhuma tarefa de alocação foi construída. "
                "Verifique se as turmas têm disciplinas e se as disciplinas têm professores."
            )
            resultado.completa = False
            return resultado

        resultado.total_blocos_necessarios = len(tarefas)
        tarefas = self._ordenar_por_prioridade(tarefas)

        logger.info(
            "Iniciando Backtracking: %d blocos a alocar em %d slots disponíveis.",
            len(tarefas),
            len(self._todos_slots),
        )

        # Etapa 3 — backtracking
        estado = _EstadoBacktrack()
        contagem = [0]  # mutável para ser modificado dentro da recursão

        try:
            sucesso = self._backtrack(0, tarefas, estado, contagem)
            if sucesso:
                logger.info(
                    "Backtracking completo com sucesso em %d iterações.", contagem[0]
                )
            else:
                # Backtracking esgotou os candidatos (sem timeout): situação impossível
                resultado.avisos.append(
                    f"Backtracking esgotou todos os candidatos após {contagem[0]} iterações. "
                    "Executando passe guloso para grade parcial..."
                )
                self._passe_guloso(tarefas, estado, resultado)

        except _BacktrackingTimeout:
            # O limite foi atingido; o estado preserva alocações já feitas
            resultado.avisos.append(
                f"⚠️  Limite de {self._max_iter:,} iterações atingido no backtracking. "
                "Estado parcial preservado. Executando passe guloso para os blocos restantes..."
            )
            logger.warning(
                "BacktrackingTimeout após %d iterações. Executando passe guloso.", contagem[0]
            )
            self._passe_guloso(tarefas, estado, resultado)

        # Etapa 4 — popula resultado
        resultado.aulas = list(estado.aulas)
        resultado.total_blocos_alocados = len(resultado.aulas)
        resultado.completa = (
            resultado.total_blocos_alocados == resultado.total_blocos_necessarios
            and resultado.total_blocos_necessarios > 0
        )

        if not resultado.completa and resultado.total_blocos_necessarios > 0:
            pct = (resultado.total_blocos_alocados / resultado.total_blocos_necessarios) * 100
            resultado.falhas.insert(
                0,
                f"❌ Grade PARCIAL: {resultado.total_blocos_alocados}/"
                f"{resultado.total_blocos_necessarios} blocos alocados "
                f"({pct:.1f}%). Consulte os diagnósticos abaixo.",
            )

        logger.info("Geração finalizada.\n%s", resultado.resumo())
        return resultado

    # ------------------------------------------------------------------
    # Backtracking recursivo
    # ------------------------------------------------------------------

    def _backtrack(
        self,
        index: int,
        tarefas: List[Tarefa],
        estado: _EstadoBacktrack,
        contagem: List[int],
    ) -> bool:
        """
        Backtracking recursivo sobre a lista de tarefas.

        Retorna True quando todas as tarefas (de index em diante) foram
        alocadas com sucesso. Retorna False quando nenhum candidato funciona
        para a tarefa atual (sinaliza para o nível superior desfazer e tentar
        outra combinação).

        Levanta _BacktrackingTimeout quando o limite de iterações é atingido;
        neste caso, o estado parcial é PRESERVADO (não desfeito) para que o
        passe guloso possa continuar a partir dali.
        """
        contagem[0] += 1
        if contagem[0] > self._max_iter:
            raise _BacktrackingTimeout()

        if index >= len(tarefas):
            return True  # ✅ Todas as tarefas alocadas!

        tarefa = tarefas[index]
        candidatos = self._candidatos_para_tarefa(tarefa, estado)

        for slot, sala in candidatos:
            aula = estado.alocar(tarefa, slot, sala)

            try:
                if self._backtrack(index + 1, tarefas, estado, contagem):
                    return True
            except _BacktrackingTimeout:
                # Não desfaz — sobe a exceção com o estado parcial intacto
                raise

            # Esta escolha não levou a uma solução → desfaz e tenta a próxima
            estado.desalocar(aula)

        # Nenhum candidato funcionou → sinaliza falha para o nível superior
        return False

    # ------------------------------------------------------------------
    # Passe guloso (fallback pós-backtracking)
    # ------------------------------------------------------------------

    def _passe_guloso(
        self,
        tarefas: List[Tarefa],
        estado: _EstadoBacktrack,
        resultado: ResultadoGrade,
    ) -> None:
        """
        Percorre todas as tarefas em ordem de prioridade e tenta alocá-las
        sem backtrack — simplesmente escolhe o primeiro candidato válido.

        É chamado quando:
        a) O backtracking retornou False (impossível com a ordenação atual).
        b) O backtracking atingiu o timeout (estado tem alocações parciais).

        Falhas são diagnosticadas com mensagem detalhada por grupo
        (turma, disciplina), evitando repetições.
        """
        falhas_por_grupo: Set[ChaveGrupo] = set()

        for tarefa in tarefas:
            chave = tarefa.chave_grupo
            # Quantos blocos deste grupo já foram alocados (backtracking + guloso)
            ja_alocados = estado.blocos_alocados_do_grupo(chave)
            if ja_alocados >= tarefa.disciplina.carga_horaria_semanal:
                continue  # Grupo já completo

            candidatos = self._candidatos_para_tarefa(tarefa, estado)
            if candidatos:
                estado.alocar(tarefa, candidatos[0][0], candidatos[0][1])
            else:
                if chave not in falhas_por_grupo:
                    self._registrar_falha_detalhada(tarefa, resultado, estado)
                    falhas_por_grupo.add(chave)
                else:
                    resultado.falhas.append(
                        f"  ↳ Bloco {tarefa.numero_bloco_disc} de "
                        f"'{tarefa.disciplina.nome}' / '{tarefa.turma.nome}' "
                        "também não pôde ser alocado (mesma causa acima)."
                    )

    # ------------------------------------------------------------------
    # Candidatos válidos para uma tarefa
    # ------------------------------------------------------------------

    def _candidatos_para_tarefa(
        self,
        tarefa: Tarefa,
        estado: _EstadoBacktrack,
    ) -> List[Tuple[Slot, Sala]]:
        """
        Retorna pares (slot, sala) válidos para a tarefa, respeitando
        todas as restrições de negócio.

        Ordenação dos slots (heurística):
          1. Dias não usados por esta (turma, disciplina) — distribui blocos.
          2. Ordem natural de dia e número de bloco.
        """
        salas_validas = [
            s for s in self._salas
            if s.comporta_turma(tarefa.turma.quantidade_alunos)
        ]
        if not salas_validas:
            return []

        dias_usados = (
            estado.dias_usados_pelo_grupo(tarefa.chave_grupo)
            if self._preferir_dias_distintos
            else set()
        )

        # Ordena: dias novos antes de dias já usados (distribuição de carga)
        slots_ordenados = sorted(
            self._todos_slots,
            key=lambda s: (1 if s[0] in dias_usados else 0, s[0], s[1]),
        )

        candidatos: List[Tuple[Slot, Sala]] = []
        id_prof = tarefa.professor.id_professor
        id_turma = tarefa.turma.id_turma

        for slot in slots_ordenados:
            dia, _ = slot

            # Restrição 1: disponibilidade do professor no dia
            if not tarefa.professor.esta_disponivel_em(dia):
                continue

            # Restrição 2: professor não tem outra aula neste slot
            if not estado.professor_livre(id_prof, slot):
                continue

            # Restrição 3: turma não tem outra aula neste slot
            if not estado.turma_livre(id_turma, slot):
                continue

            # Restrição 4: sala disponível com capacidade suficiente
            for sala in salas_validas:
                if estado.sala_livre(sala.id_sala, slot):
                    candidatos.append((slot, sala))
                    break  # Usa a primeira sala válida para este slot

        return candidatos

    # ------------------------------------------------------------------
    # Diagnóstico detalhado de falha
    # ------------------------------------------------------------------

    def _registrar_falha_detalhada(
        self,
        tarefa: Tarefa,
        resultado: ResultadoGrade,
        estado: _EstadoBacktrack,
    ) -> None:
        """
        Analisa e registra a causa específica da impossibilidade de alocação.
        Percorre diagnósticos em cascata para identificar o gargalo exato.
        """
        prof = tarefa.professor
        turma = tarefa.turma
        disc = tarefa.disciplina
        prefixo = f"❌ [FALHA] '{disc.nome}' para turma '{turma.nome}'"

        # Diagnóstico 1: professor sem nenhum dia disponível
        if not prof.dias_disponiveis:
            resultado.falhas.append(
                f"{prefixo}: o professor '{prof.nome}' (ID {prof.id_professor}) "
                "não possui nenhum dia disponível cadastrado. Impossível alocar qualquer bloco."
            )
            return

        # Diagnóstico 2: todos os slots do professor estão ocupados
        slots_do_prof = [s for s in self._todos_slots if prof.esta_disponivel_em(s[0])]
        slots_livres_prof = [
            s for s in slots_do_prof if estado.professor_livre(prof.id_professor, s)
        ]
        if not slots_livres_prof:
            resultado.falhas.append(
                f"{prefixo}: o professor '{prof.nome}' (ID {prof.id_professor}) "
                f"não possui mais slots livres em seus {len(prof.dias_disponiveis)} dia(s) "
                f"disponível(is): {prof.dias_disponiveis}. "
                f"Total de slots permitidos: {len(slots_do_prof)}, todos ocupados."
            )
            return

        # Diagnóstico 3: turma sem slots que coincidam com o professor
        slots_livres_ambos = [
            s for s in slots_livres_prof
            if estado.turma_livre(turma.id_turma, s)
        ]
        if not slots_livres_ambos:
            resultado.falhas.append(
                f"{prefixo}: não há slot simultaneamente livre para o professor "
                f"'{prof.nome}' e a turma '{turma.nome}'. "
                f"O professor tem {len(slots_livres_prof)} slot(s) livre(s), mas a turma "
                "já está ocupada em todos eles."
            )
            return

        # Diagnóstico 4: nenhuma sala com capacidade suficiente
        salas_validas = [s for s in self._salas if s.comporta_turma(turma.quantidade_alunos)]
        if not salas_validas:
            maior_cap = max(s.capacidade for s in self._salas) if self._salas else 0
            resultado.falhas.append(
                f"{prefixo}: a turma tem {turma.quantidade_alunos} alunos, mas nenhuma "
                f"sala comporta esse número (maior capacidade disponível: {maior_cap} vagas). "
                "Cadastre uma sala adequada."
            )
            return

        # Diagnóstico 5: salas com capacidade, mas todas ocupadas nos slots válidos
        slots_com_sala_livre = [
            s for s in slots_livres_ambos
            if any(estado.sala_livre(sala.id_sala, s) for sala in salas_validas)
        ]
        if not slots_com_sala_livre:
            resultado.falhas.append(
                f"{prefixo}: há {len(slots_livres_ambos)} slot(s) livre(s) para professor "
                f"e turma, mas todas as {len(salas_validas)} sala(s) com capacidade suficiente "
                "estão ocupadas nesses slots. Adicione mais salas ou reduza a carga horária."
            )
            return

        # Diagnóstico genérico (não deveria ocorrer se os candidatos forem calculados corretamente)
        resultado.falhas.append(
            f"{prefixo}: bloco {tarefa.numero_bloco_disc} não pôde ser alocado. "
            "Causa indeterminada — revise manualmente os dados."
        )

    # ------------------------------------------------------------------
    # Construção das tarefas
    # ------------------------------------------------------------------

    def _construir_tarefas(self, resultado: ResultadoGrade) -> List[Tarefa]:
        """
        Para cada (turma, disciplina) cria N instâncias de Tarefa,
        onde N = carga_horaria_semanal da disciplina.

        Registra aviso se disciplina não tiver professor associado.
        """
        tarefas: List[Tarefa] = []
        professores = self._rl.professores
        disciplinas = self._rl.disciplinas

        for turma in self._rl.turmas.values():
            for id_disc in turma.id_disciplinas:
                disc = disciplinas.get(id_disc)
                if disc is None:
                    resultado.falhas.append(
                        f"⚠️  Turma '{turma.nome}': disciplina ID={id_disc} "
                        "não encontrada em Disciplinas.csv. Ignorada na geração."
                    )
                    continue

                if disc.id_professor is None:
                    resultado.falhas.append(
                        f"⚠️  Disciplina '{disc.nome}' (ID={disc.id_disciplina}) "
                        "não possui professor associado. "
                        "Adicione id_professor em Disciplinas.csv para esta disciplina."
                    )
                    continue

                prof = professores.get(disc.id_professor)
                if prof is None:
                    resultado.falhas.append(
                        f"⚠️  Disciplina '{disc.nome}': professor ID={disc.id_professor} "
                        "não encontrado em Professores.csv. Disciplina ignorada na geração."
                    )
                    continue

                for bloco_n in range(1, disc.carga_horaria_semanal + 1):
                    tarefas.append(
                        Tarefa(
                            turma=turma,
                            disciplina=disc,
                            professor=prof,
                            numero_bloco_disc=bloco_n,
                        )
                    )

        return tarefas

    def _ordenar_por_prioridade(self, tarefas: List[Tarefa]) -> List[Tarefa]:
        """
        Ordena tarefas do mais restritivo para o menos restritivo.
        Critérios (em ordem de desempate):
          1. Professor com menos dias disponíveis (melhor alocar primeiro).
          2. Disciplina com maior carga horária (mais difícil de espalhar).
          3. Número do bloco (consistência dentro do mesmo grupo).
        """
        return sorted(tarefas, key=lambda t: t.prioridade)

    # ------------------------------------------------------------------
    # Validações de pré-condição
    # ------------------------------------------------------------------

    def _validar_pre_geracao(self, resultado: ResultadoGrade) -> bool:
        """
        Verifica viabilidade mínima antes de iniciar o algoritmo.
        Retorna False se a geração deve ser abortada imediatamente.
        """
        rl = self._rl
        ok = True

        if not rl.turmas:
            resultado.falhas.append(
                "❌ Nenhuma turma carregada. Carregue Turmas.csv antes de gerar."
            )
            ok = False

        if not rl.professores:
            resultado.falhas.append(
                "❌ Nenhum professor carregado. Carregue Professores.csv antes de gerar."
            )
            ok = False

        if not rl.salas:
            resultado.falhas.append(
                "❌ Nenhuma sala carregada. Carregue Salas.csv antes de gerar."
            )
            ok = False

        if not ok:
            return False

        # Verifica se a capacidade total da grade comporta todos os blocos
        total_slots = len(self._todos_slots)
        total_salas = len(self._salas)
        capacidade_maxima = total_slots * total_salas

        total_blocos = sum(
            disc.carga_horaria_semanal
            for turma in rl.turmas.values()
            for id_disc in turma.id_disciplinas
            if (disc := rl.disciplinas.get(id_disc)) is not None
            and disc.id_professor is not None
        )

        if total_blocos > capacidade_maxima:
            resultado.falhas.append(
                f"❌ Capacidade insuficiente: {total_blocos} blocos necessários, "
                f"mas a grade comporta no máximo {capacidade_maxima} "
                f"({total_slots} slots × {total_salas} salas). "
                "Adicione mais salas ou aumente os blocos por dia."
            )
            ok = False

        # Verifica professores sem nenhum dia disponível
        for prof in rl.professores.values():
            if not prof.dias_disponiveis:
                resultado.avisos.append(
                    f"⚠️  Professor '{prof.nome}' (ID {prof.id_professor}) "
                    "não tem dias disponíveis. Suas disciplinas não serão alocadas."
                )

        return ok
