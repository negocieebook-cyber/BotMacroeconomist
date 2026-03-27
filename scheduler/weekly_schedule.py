"""
Agendador semanal para coleta automatica de dados.
"""

from datetime import datetime, timezone
import logging
from typing import Callable, Dict

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class WeeklyScheduler:
    """Agendador de tarefas semanais."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.configure(timezone=timezone.utc)
        self.jobs = {}

    def schedule_task(
        self,
        task_name: str,
        task_func: Callable,
        weekday: str,
        hour: int,
        minute: int = 0,
    ) -> None:
        """Agenda uma tarefa para um dia/hora especifico."""
        try:
            trigger = CronTrigger(
                day_of_week=self._weekday_to_cron(weekday),
                hour=hour,
                minute=minute,
                timezone=timezone.utc,
            )

            job = self.scheduler.add_job(
                task_func,
                trigger=trigger,
                id=f"{task_name}_{weekday}_{hour}:{minute}",
                name=task_name,
                replace_existing=True,
            )

            self.jobs[task_name] = job
            logger.info(
                f"Tarefa '{task_name}' agendada para {weekday} as {hour:02d}:{minute:02d} UTC"
            )

        except Exception as e:
            logger.error(f"Erro ao agendar tarefa {task_name}: {str(e)}")
            raise

    def schedule_daily_task(
        self,
        task_name: str,
        task_func: Callable,
        hour: int,
        minute: int = 0,
    ) -> None:
        """Agenda uma tarefa diaria em horario UTC."""
        try:
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                timezone=timezone.utc,
            )

            job = self.scheduler.add_job(
                task_func,
                trigger=trigger,
                id=f"{task_name}_daily_{hour}:{minute}",
                name=task_name,
                replace_existing=True,
            )

            self.jobs[task_name] = job
            logger.info(
                f"Tarefa diaria '{task_name}' agendada para {hour:02d}:{minute:02d} UTC"
            )
        except Exception as e:
            logger.error(f"Erro ao agendar tarefa diaria {task_name}: {str(e)}")
            raise

    def schedule_from_config(self, schedule_config: Dict) -> None:
        """Agenda tarefas a partir de um dicionario de configuracao simples."""
        for task_name, task_config in schedule_config.items():
            task_func = task_config.get("task_func")
            weekday = task_config.get("weekday", task_name)
            hour = int(task_config.get("hour", 14))
            minute = int(task_config.get("minute", 0))

            if callable(task_func):
                self.schedule_task(task_name, task_func, weekday, hour, minute)
            else:
                logger.warning(
                    f"Tarefa '{task_name}' ignorada em schedule_from_config: task_func nao informado"
                )

    def start(self) -> None:
        """Inicia o scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler iniciado")

    def stop(self) -> None:
        """Para o scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler parado")

    def get_jobs(self) -> Dict:
        """Retorna lista de tarefas agendadas."""
        jobs_info = {}
        for job in self.scheduler.get_jobs():
            jobs_info[job.name] = {
                "id": job.id,
                "next_run_time": str(job.next_run_time),
                "trigger": str(job.trigger),
            }
        return jobs_info

    def _weekday_to_cron(self, weekday: str) -> str:
        """Converte nome do dia para formato cron."""
        mapping = {
            "segunda": "0",
            "terca": "1",
            "terca-feira": "1",
            "terca_feira": "1",
            "terça": "1",
            "quarta": "2",
            "quinta": "3",
            "sexta": "4",
            "sabado": "5",
            "sábado": "5",
            "domingo": "6",
            "monday": "0",
            "tuesday": "1",
            "wednesday": "2",
            "thursday": "3",
            "friday": "4",
            "saturday": "5",
            "sunday": "6",
        }
        return mapping.get(weekday.lower(), "0")


class TaskManager:
    """Gerenciador simples de execucao de tarefas."""

    def __init__(self):
        self.tasks_history = []
        self.current_task = None

    def log_task_execution(
        self,
        task_name: str,
        status: str,
        result: dict = None,
        error: str = None,
    ) -> None:
        """Registra execucao de uma tarefa."""
        execution_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "task": task_name,
            "status": status,
            "result": result,
            "error": error,
        }

        self.tasks_history.append(execution_log)

        if status == "completed":
            logger.info(f"{task_name}: concluida")
        elif status == "failed":
            logger.error(f"{task_name}: erro - {error}")
        elif status == "started":
            logger.info(f"{task_name}: iniciada")

    def get_history(self, limit: int = 10) -> list:
        """Retorna historico de execucao."""
        return self.tasks_history[-limit:]

    def get_stats(self) -> dict:
        """Retorna estatisticas de execucao."""
        if not self.tasks_history:
            return {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
            }

        successful = len([t for t in self.tasks_history if t["status"] == "completed"])
        failed = len([t for t in self.tasks_history if t["status"] == "failed"])
        total = len(self.tasks_history)

        return {
            "total_executions": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0.0,
        }
