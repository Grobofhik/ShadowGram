from apscheduler.schedulers.qt import QtScheduler
from src.core.logger import logger

class AppScheduler:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppScheduler, cls).__new__(cls)
            cls._instance.scheduler = QtScheduler()
            cls._instance.scheduler.start()
            logger.info("APScheduler (QtScheduler) запущен.")
        return cls._instance

    def add_job(self, func, trigger, **kwargs):
        """Добавить задачу в расписание. Например: trigger='interval', hours=1"""
        try:
            job = self.scheduler.add_job(func, trigger, **kwargs)
            logger.info(f"Задача добавлена в расписание: {job.id}")
            return job.id
        except Exception as e:
            logger.error(f"Ошибка при добавлении задачи: {e}")
            return None

    def remove_job(self, job_id):
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Задача удалена: {job_id}")
        except Exception as e:
            logger.error(f"Ошибка при удалении задачи: {e}")

    def get_jobs(self):
        return self.scheduler.get_jobs()

# Глобальный инстанс
global_scheduler = AppScheduler()
