"""
LeitorCSV — Responsável por toda a leitura e validação dos arquivos CSV.

Responsabilidades
-----------------
1. Ler cada CSV com Pandas, tratando separadores e encoding.
2. Parsear campos multivalorados separados por ';' em listas de IDs.
3. Validar tipos e presença de colunas obrigatórias.
4. Detectar IDs órfãos (referências que não existem na entidade-pai).
5. Acumular e expor todas as inconsistências encontradas sem parar na
   primeira falha, permitindo que a interface exiba um relatório completo.
6. Construir e retornar os objetos de domínio (Professor, Disciplina,
   Sala, Turma) prontos para uso pelo GeradorDeGrade.

Formato esperado dos CSVs
--------------------------
Professores.csv  → colunas: id_professor, nome, dias_disponiveis
Disciplinas.csv  → colunas: id_disciplina, nome, carga_horaria_semanal
                             [opcional: id_professor]
Turmas.csv       → colunas: id_turma, nome, curso, id_disciplinas,
                             quantidade_alunos  (aceita também qtd_alunos)
Salas.csv        → colunas: id_sala, numero, capacidade
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from organizador_aulas.models import Disciplina, Professor, Sala, Turma
from organizador_aulas.models.professor import normalizar_dia

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes de colunas obrigatórias
# ---------------------------------------------------------------------------

_COLUNAS_PROFESSORES: List[str] = ["id_professor", "nome", "dias_disponiveis"]
_COLUNAS_DISCIPLINAS: List[str] = ["id_disciplina", "nome", "carga_horaria_semanal"]
_COLUNAS_TURMAS_BASE: List[str] = ["id_turma", "nome", "curso", "id_disciplinas"]
_COLUNAS_SALAS: List[str] = ["id_sala", "numero", "capacidade"]

# Aliases aceitos para a coluna de quantidade de alunos em Turmas.csv
_ALIAS_QTD_ALUNOS = ["quantidade_alunos", "qtd_alunos", "num_alunos", "alunos"]


# ---------------------------------------------------------------------------
# Dataclass de resultado
# ---------------------------------------------------------------------------


@dataclass
class ResultadoLeitura:
    """
    Encapsula o resultado completo de uma operação de leitura de CSVs.

    Atributos
    ----------
    professores : Dict[int, Professor]
        Mapa id_professor → objeto Professor.
    disciplinas : Dict[int, Disciplina]
        Mapa id_disciplina → objeto Disciplina.
    salas : Dict[int, Sala]
        Mapa id_sala → objeto Sala.
    turmas : Dict[int, Turma]
        Mapa id_turma → objeto Turma.
    inconsistencias : List[str]
        Mensagens de erro/aviso acumuladas durante a leitura e validação.
    sucesso : bool
        False se houver pelo menos um erro crítico (colunas faltando,
        IDs duplicados, IDs órfãos). Avisos não bloqueantes mantêm True.
    """

    professores: Dict[int, Professor] = field(default_factory=dict)
    disciplinas: Dict[int, Disciplina] = field(default_factory=dict)
    salas: Dict[int, Sala] = field(default_factory=dict)
    turmas: Dict[int, Turma] = field(default_factory=dict)
    inconsistencias: List[str] = field(default_factory=list)
    sucesso: bool = True

    def tem_erros(self) -> bool:
        return not self.sucesso

    def resumo(self) -> str:
        linhas = [
            f"Professores carregados : {len(self.professores)}",
            f"Disciplinas carregadas : {len(self.disciplinas)}",
            f"Salas carregadas       : {len(self.salas)}",
            f"Turmas carregadas      : {len(self.turmas)}",
            f"Inconsistências        : {len(self.inconsistencias)}",
        ]
        return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Classe principal
# ---------------------------------------------------------------------------


class LeitorCSV:
    """
    Lê e valida todos os arquivos CSV do projeto Organizador de Aulas.

    Uso básico
    ----------
    >>> leitor = LeitorCSV(pasta_csv="dados/csv")
    >>> resultado = leitor.carregar_tudo()
    >>> if resultado.tem_erros():
    ...     for msg in resultado.inconsistencias:
    ...         print(msg)
    ... else:
    ...     print(resultado.resumo())

    Parâmetros
    ----------
    pasta_csv : str | Path
        Caminho para o diretório que contém os arquivos CSV.
        Os nomes padrão esperados são: Professores.csv, Disciplinas.csv,
        Turmas.csv e Salas.csv. Paths individuais podem ser sobrescritos
        pelos parâmetros opcionais do método carregar_tudo().
    encoding : str
        Encoding para leitura dos CSVs (padrão: 'utf-8-sig' para suportar
        arquivos gerados pelo Excel com BOM).
    separador_csv : str
        Delimitador de colunas no CSV (padrão: ',').
    """

    def __init__(
        self,
        pasta_csv: str | Path = ".",
        encoding: str = "utf-8-sig",
        separador_csv: str = ",",
    ) -> None:
        self._pasta = Path(pasta_csv)
        self._encoding = encoding
        self._sep = separador_csv

        # Resultado acumulado — recriado a cada chamada de carregar_tudo()
        self._resultado: ResultadoLeitura = ResultadoLeitura()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def carregar_tudo(
        self,
        path_professores: Optional[str | Path] = None,
        path_disciplinas: Optional[str | Path] = None,
        path_turmas: Optional[str | Path] = None,
        path_salas: Optional[str | Path] = None,
    ) -> ResultadoLeitura:
        """
        Ponto de entrada principal. Lê todos os CSVs e retorna um
        ResultadoLeitura com as entidades e as inconsistências detectadas.

        Parâmetros
        ----------
        path_* : str | Path | None
            Caminhos individuais para cada CSV. Se None, assume o arquivo
            padrão dentro de pasta_csv.

        Retorno
        -------
        ResultadoLeitura
            Objeto populado com entidades e lista de inconsistências.
        """
        self._resultado = ResultadoLeitura()

        paths = {
            "professores": self._resolve(path_professores, "Professores.csv"),
            "disciplinas": self._resolve(path_disciplinas, "Disciplinas.csv"),
            "turmas": self._resolve(path_turmas, "Turmas.csv"),
            "salas": self._resolve(path_salas, "Salas.csv"),
        }

        # --- 1. Ler DataFrames brutos ---
        dfs: Dict[str, Optional[pd.DataFrame]] = {}
        for nome, caminho in paths.items():
            dfs[nome] = self._ler_csv(caminho, nome)

        # --- 2. Parsear cada entidade (dependências primeiro) ---
        if dfs["professores"] is not None:
            self._resultado.professores = self._parsear_professores(dfs["professores"])

        if dfs["disciplinas"] is not None:
            self._resultado.disciplinas = self._parsear_disciplinas(dfs["disciplinas"])

        if dfs["salas"] is not None:
            self._resultado.salas = self._parsear_salas(dfs["salas"])

        if dfs["turmas"] is not None:
            self._resultado.turmas = self._parsear_turmas(dfs["turmas"])

        # --- 3. Validação cruzada de IDs (órfãos) ---
        self._validar_ids_cruzados()

        # --- 4. Marca sucesso/falha ---
        if self._resultado.inconsistencias:
            self._resultado.sucesso = False

        logger.info("Leitura concluída. %s", self._resultado.resumo())
        return self._resultado

    # ------------------------------------------------------------------
    # Leitura de arquivo
    # ------------------------------------------------------------------

    def _resolve(self, path_override: Optional[str | Path], nome_padrao: str) -> Path:
        """Retorna o path definitivo para um CSV."""
        if path_override is not None:
            return Path(path_override)
        return self._pasta / nome_padrao

    def _ler_csv(self, caminho: Path, nome_entidade: str) -> Optional[pd.DataFrame]:
        """
        Lê um arquivo CSV com Pandas.

        Retorna None e registra uma inconsistência se:
        - o arquivo não existir.
        - o arquivo estiver vazio.
        - houver erro de parsing.
        """
        if not caminho.exists():
            self._erro(
                f"[{nome_entidade.upper()}] Arquivo não encontrado: '{caminho}'. "
                "Nenhuma entidade deste tipo será carregada."
            )
            return None

        try:
            df = pd.read_csv(
                caminho,
                sep=self._sep,
                encoding=self._encoding,
                dtype=str,          # tudo como string; conversão feita manualmente
                skipinitialspace=True,
            )
        except Exception as exc:
            self._erro(
                f"[{nome_entidade.upper()}] Falha ao ler '{caminho}': {exc}"
            )
            return None

        # Remove espaços dos nomes de colunas (tolerância a espaços extras no CSV)
        df.columns = [col.strip().lower() for col in df.columns]

        if df.empty:
            self._aviso(
                f"[{nome_entidade.upper()}] Arquivo '{caminho.name}' está vazio."
            )
            return df  # retorna vazio mas não bloqueia

        logger.debug(
            "CSV '%s' lido: %d linhas, colunas=%s",
            caminho.name, len(df), df.columns.tolist()
        )
        return df

    # ------------------------------------------------------------------
    # Parsers por entidade
    # ------------------------------------------------------------------

    def _parsear_professores(self, df: pd.DataFrame) -> Dict[int, Professor]:
        """
        Parseia o DataFrame de professores em objetos Professor.

        Valida:
        - Colunas obrigatórias presentes.
        - IDs inteiros únicos e não nulos.
        - Dias disponíveis reconhecidos.
        """
        entidade = "PROFESSORES"
        if not self._checar_colunas(df, _COLUNAS_PROFESSORES, entidade):
            return {}

        professores: Dict[int, Professor] = {}
        ids_vistos: set[int] = set()

        for idx, row in df.iterrows():
            linha = idx + 2  # +2 = cabeçalho (1) + índice zero-based (1)

            # --- ID ---
            id_prof = self._parse_int(row.get("id_professor"), entidade, linha, "id_professor")
            if id_prof is None:
                continue

            if id_prof in ids_vistos:
                self._erro(
                    f"[{entidade}] Linha {linha}: id_professor={id_prof} duplicado. "
                    "Registro ignorado."
                )
                continue
            ids_vistos.add(id_prof)

            # --- Nome ---
            nome = self._parse_str(row.get("nome"), entidade, linha, "nome")
            if nome is None:
                continue

            # --- Dias disponíveis ---
            dias_raw = self._parse_str(
                row.get("dias_disponiveis"), entidade, linha, "dias_disponiveis"
            )
            dias: List[str] = []
            if dias_raw:
                for parte in self._split_semicolon(dias_raw):
                    try:
                        dias.append(normalizar_dia(parte))
                    except ValueError as exc:
                        self._erro(
                            f"[{entidade}] Linha {linha}, professor '{nome}': {exc}"
                        )

            if not dias:
                self._aviso(
                    f"[{entidade}] Linha {linha}: professor '{nome}' "
                    "(ID {id_prof}) não possui dias disponíveis válidos. "
                    "Não poderá ser alocado."
                )

            # --- Construção do objeto ---
            try:
                prof = Professor(
                    id_professor=id_prof,
                    nome=nome,
                    dias_disponiveis=dias,  # já normalizados, __post_init__ é idempotente
                )
                professores[id_prof] = prof
            except Exception as exc:
                self._erro(
                    f"[{entidade}] Linha {linha}: erro ao construir Professor: {exc}"
                )

        return professores

    def _parsear_disciplinas(self, df: pd.DataFrame) -> Dict[int, Disciplina]:
        """
        Parseia o DataFrame de disciplinas em objetos Disciplina.

        Valida:
        - Colunas obrigatórias presentes.
        - IDs inteiros únicos e não nulos.
        - carga_horaria_semanal positiva.
        - id_professor (opcional) é inteiro válido se presente.
        """
        entidade = "DISCIPLINAS"
        if not self._checar_colunas(df, _COLUNAS_DISCIPLINAS, entidade):
            return {}

        tem_col_professor = "id_professor" in df.columns
        disciplinas: Dict[int, Disciplina] = {}
        ids_vistos: set[int] = set()

        for idx, row in df.iterrows():
            linha = idx + 2

            # --- ID ---
            id_disc = self._parse_int(
                row.get("id_disciplina"), entidade, linha, "id_disciplina"
            )
            if id_disc is None:
                continue

            if id_disc in ids_vistos:
                self._erro(
                    f"[{entidade}] Linha {linha}: id_disciplina={id_disc} duplicado. "
                    "Registro ignorado."
                )
                continue
            ids_vistos.add(id_disc)

            # --- Nome ---
            nome = self._parse_str(row.get("nome"), entidade, linha, "nome")
            if nome is None:
                continue

            # --- Carga horária ---
            carga = self._parse_int(
                row.get("carga_horaria_semanal"), entidade, linha, "carga_horaria_semanal"
            )
            if carga is None:
                continue
            if carga < 1:
                self._erro(
                    f"[{entidade}] Linha {linha}: carga_horaria_semanal={carga} "
                    f"para '{nome}' é inválida (mín. 1 bloco de 50 min)."
                )
                continue

            # --- id_professor (opcional) ---
            id_prof: Optional[int] = None
            if tem_col_professor:
                val = row.get("id_professor")
                if pd.notna(val) and str(val).strip():
                    id_prof = self._parse_int(val, entidade, linha, "id_professor")

            # --- Construção ---
            try:
                disc = Disciplina(
                    id_disciplina=id_disc,
                    nome=nome,
                    carga_horaria_semanal=carga,
                    id_professor=id_prof,
                )
                disciplinas[id_disc] = disc
            except Exception as exc:
                self._erro(
                    f"[{entidade}] Linha {linha}: erro ao construir Disciplina: {exc}"
                )

        return disciplinas

    def _parsear_salas(self, df: pd.DataFrame) -> Dict[int, Sala]:
        """
        Parseia o DataFrame de salas em objetos Sala.

        Valida:
        - Colunas obrigatórias presentes.
        - IDs inteiros únicos.
        - Capacidade positiva.
        """
        entidade = "SALAS"
        if not self._checar_colunas(df, _COLUNAS_SALAS, entidade):
            return {}

        salas: Dict[int, Sala] = {}
        ids_vistos: set[int] = set()

        for idx, row in df.iterrows():
            linha = idx + 2

            # --- ID ---
            id_sala = self._parse_int(row.get("id_sala"), entidade, linha, "id_sala")
            if id_sala is None:
                continue

            if id_sala in ids_vistos:
                self._erro(
                    f"[{entidade}] Linha {linha}: id_sala={id_sala} duplicado. "
                    "Registro ignorado."
                )
                continue
            ids_vistos.add(id_sala)

            # --- Número ---
            numero = self._parse_str(row.get("numero"), entidade, linha, "numero")
            if numero is None:
                continue

            # --- Capacidade ---
            cap = self._parse_int(row.get("capacidade"), entidade, linha, "capacidade")
            if cap is None:
                continue
            if cap < 1:
                self._erro(
                    f"[{entidade}] Linha {linha}: capacidade={cap} na sala '{numero}' "
                    "é inválida (mín. 1)."
                )
                continue

            # --- Construção ---
            try:
                sala = Sala(id_sala=id_sala, numero=numero, capacidade=cap)
                salas[id_sala] = sala
            except Exception as exc:
                self._erro(
                    f"[{entidade}] Linha {linha}: erro ao construir Sala: {exc}"
                )

        return salas

    def _parsear_turmas(self, df: pd.DataFrame) -> Dict[int, Turma]:
        """
        Parseia o DataFrame de turmas em objetos Turma.

        Valida:
        - Colunas obrigatórias presentes (aceita aliases para qtd_alunos).
        - IDs inteiros únicos.
        - id_disciplinas: parseia lista separada por ';', converte para int.
        - quantidade_alunos: inteiro não-negativo.
        """
        entidade = "TURMAS"

        # Normaliza o nome da coluna de quantidade de alunos
        col_alunos = self._detectar_coluna_alunos(df)
        if not self._checar_colunas(df, _COLUNAS_TURMAS_BASE, entidade):
            return {}
        if col_alunos is None:
            self._erro(
                f"[{entidade}] Nenhuma coluna de quantidade de alunos encontrada. "
                f"Aceitas: {_ALIAS_QTD_ALUNOS}. Turmas não serão carregadas."
            )
            return {}

        turmas: Dict[int, Turma] = {}
        ids_vistos: set[int] = set()

        for idx, row in df.iterrows():
            linha = idx + 2

            # --- ID ---
            id_turma = self._parse_int(row.get("id_turma"), entidade, linha, "id_turma")
            if id_turma is None:
                continue

            if id_turma in ids_vistos:
                self._erro(
                    f"[{entidade}] Linha {linha}: id_turma={id_turma} duplicado. "
                    "Registro ignorado."
                )
                continue
            ids_vistos.add(id_turma)

            # --- Nome ---
            nome = self._parse_str(row.get("nome"), entidade, linha, "nome")
            if nome is None:
                continue

            # --- Curso ---
            curso = self._parse_str(row.get("curso"), entidade, linha, "curso")
            if curso is None:
                continue

            # --- IDs de disciplinas (campo multivalorado) ---
            discs_raw = self._parse_str(
                row.get("id_disciplinas"), entidade, linha, "id_disciplinas"
            )
            id_disciplinas: List[int] = []
            if discs_raw:
                for parte in self._split_semicolon(discs_raw):
                    disc_id = self._parse_int(
                        parte, entidade, linha, f"id_disciplinas['{parte}']"
                    )
                    if disc_id is not None:
                        id_disciplinas.append(disc_id)
            if not id_disciplinas:
                self._aviso(
                    f"[{entidade}] Linha {linha}: turma '{nome}' não possui "
                    "disciplinas associadas."
                )

            # --- Quantidade de alunos ---
            qtd_alunos = self._parse_int(
                row.get(col_alunos), entidade, linha, col_alunos
            )
            qtd_alunos = qtd_alunos if qtd_alunos is not None else 0
            if qtd_alunos < 0:
                self._erro(
                    f"[{entidade}] Linha {linha}: {col_alunos}={qtd_alunos} "
                    f"na turma '{nome}' é inválido."
                )
                continue

            # --- Construção ---
            try:
                turma = Turma(
                    id_turma=id_turma,
                    nome=nome,
                    curso=curso,
                    id_disciplinas=id_disciplinas,
                    quantidade_alunos=qtd_alunos,
                )
                turmas[id_turma] = turma
            except Exception as exc:
                self._erro(
                    f"[{entidade}] Linha {linha}: erro ao construir Turma: {exc}"
                )

        return turmas

    # ------------------------------------------------------------------
    # Validação cruzada de IDs (órfãos)
    # ------------------------------------------------------------------

    def _validar_ids_cruzados(self) -> None:
        """
        Detecta referências de IDs que não existem na entidade-pai correspondente.

        Verificações realizadas:
        1. Disciplinas.id_professor → deve existir em Professores.
        2. Turmas.id_disciplinas (cada item) → deve existir em Disciplinas.
        """
        r = self._resultado

        # 1. Disciplinas → Professores
        if r.professores and r.disciplinas:
            ids_professores = set(r.professores.keys())
            for disc in r.disciplinas.values():
                if disc.id_professor is not None:
                    if disc.id_professor not in ids_professores:
                        self._erro(
                            f"[CRUZAMENTO] Disciplina '{disc.nome}' "
                            f"(ID {disc.id_disciplina}) referencia "
                            f"id_professor={disc.id_professor} que não existe em "
                            "Professores.csv. → ID ÓRFÃO."
                        )

        # 2. Turmas → Disciplinas
        if r.disciplinas and r.turmas:
            ids_disciplinas = set(r.disciplinas.keys())
            for turma in r.turmas.values():
                for id_disc in turma.id_disciplinas:
                    if id_disc not in ids_disciplinas:
                        self._erro(
                            f"[CRUZAMENTO] Turma '{turma.nome}' "
                            f"(ID {turma.id_turma}) referencia "
                            f"id_disciplina={id_disc} que não existe em "
                            "Disciplinas.csv. → ID ÓRFÃO."
                        )

        # 3. Aviso: disciplinas sem professor associado
        if r.disciplinas:
            for disc in r.disciplinas.values():
                if disc.id_professor is None:
                    self._aviso(
                        f"[CRUZAMENTO] Disciplina '{disc.nome}' "
                        f"(ID {disc.id_disciplina}) não possui professor associado. "
                        "A geração de grade pode falhar para esta disciplina."
                    )

    # ------------------------------------------------------------------
    # Helpers de parse
    # ------------------------------------------------------------------

    @staticmethod
    def _split_semicolon(valor: str) -> List[str]:
        """
        Divide uma string por ';' e remove espaços e valores vazios.

        Exemplo: '101;102; 103' → ['101', '102', '103']
        """
        return [parte.strip() for parte in valor.split(";") if parte.strip()]

    def _parse_int(
        self,
        valor: object,
        entidade: str,
        linha: int,
        campo: str,
    ) -> Optional[int]:
        """
        Converte valor para int. Registra erro e retorna None se falhar.
        """
        if pd.isna(valor) or str(valor).strip() == "":
            self._erro(
                f"[{entidade}] Linha {linha}: campo '{campo}' está vazio/nulo."
            )
            return None
        try:
            # float → int para tolerar '101.0' exportado por algumas planilhas
            return int(float(str(valor).strip()))
        except (ValueError, TypeError):
            self._erro(
                f"[{entidade}] Linha {linha}: campo '{campo}' com valor "
                f"'{valor}' não é um inteiro válido."
            )
            return None

    def _parse_str(
        self,
        valor: object,
        entidade: str,
        linha: int,
        campo: str,
    ) -> Optional[str]:
        """
        Garante que o valor é uma string não vazia. Registra erro se falhar.
        """
        if pd.isna(valor) or str(valor).strip() == "":
            self._erro(
                f"[{entidade}] Linha {linha}: campo '{campo}' está vazio/nulo."
            )
            return None
        return str(valor).strip()

    # ------------------------------------------------------------------
    # Helpers de validação
    # ------------------------------------------------------------------

    def _checar_colunas(
        self, df: pd.DataFrame, colunas: List[str], entidade: str
    ) -> bool:
        """
        Verifica se todas as colunas obrigatórias estão presentes no DataFrame.
        Registra erro detalhado para cada coluna ausente.

        Retorna True se todas estiverem presentes.
        """
        faltando = [col for col in colunas if col not in df.columns]
        if faltando:
            self._erro(
                f"[{entidade}] Colunas obrigatórias ausentes: {faltando}. "
                f"Colunas encontradas: {df.columns.tolist()}. "
                "Nenhuma entidade deste tipo será carregada."
            )
            return False
        return True

    def _detectar_coluna_alunos(self, df: pd.DataFrame) -> Optional[str]:
        """
        Detecta qual alias de coluna de quantidade de alunos existe no DataFrame.
        Retorna o nome da coluna encontrada ou None.
        """
        for alias in _ALIAS_QTD_ALUNOS:
            if alias in df.columns:
                return alias
        return None

    # ------------------------------------------------------------------
    # Registro de erros e avisos
    # ------------------------------------------------------------------

    def _erro(self, mensagem: str) -> None:
        """Registra um erro crítico (marca resultado como falha)."""
        logger.error(mensagem)
        self._resultado.inconsistencias.append(f"❌ ERRO: {mensagem}")
        self._resultado.sucesso = False

    def _aviso(self, mensagem: str) -> None:
        """Registra um aviso não-bloqueante."""
        logger.warning(mensagem)
        self._resultado.inconsistencias.append(f"⚠️  AVISO: {mensagem}")
