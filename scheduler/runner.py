from __future__ import annotations

from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from scheduler.daily_jobs import run_daily_pipeline
from scheduler.weekly_jobs import run_learning_pipeline, run_weekly_pipeline


def start_scheduler(base_dir: Path) -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(lambda: run_daily_pipeline(base_dir), "cron", hour=22, minute=0)
    scheduler.add_job(lambda: run_weekly_pipeline(base_dir), "cron", day_of_week="mon,thu", hour=9, minute=0)
    scheduler.add_job(lambda: run_learning_pipeline(base_dir), "cron", day_of_week="sun", hour=18, minute=0)
    scheduler.start()
