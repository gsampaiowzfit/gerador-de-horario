# organizador_aulas/models/__init__.py
from .professor import Professor
from .disciplina import Disciplina
from .sala import Sala
from .turma import Turma
from .horario import Horario
from .aula import Aula

__all__ = ["Professor", "Disciplina", "Sala", "Turma", "Horario", "Aula"]
