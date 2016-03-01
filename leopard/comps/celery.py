import datetime

from celery import Celery
from celery.schedules import crontab

task_path = 'leopard.apps.service.tasks'


def get_celery_task(task):
    return '.'.join((task_path, task))


CELERYBEAT_SCHEDULE = {
    "auto_adjust_user_level": {
        'task': get_celery_task("auto_adjust_user_level"),
        'schedule': crontab(hour=5, minute=0)
    },
    "student_loan_repay_remind": {
        'task': get_celery_task("student_loan_repay_remind"),
        'schedule': crontab(hour=9, minute=0)
    },
    "auto_check_first_record_time": {
        "task": get_celery_task("check_first_record_time"),
        "schedule": datetime.timedelta(minutes=2),
    },
    "inspect_overdue_transferring_investments": {
        "task": get_celery_task("inspect_overdue_transferring_investments"),
        "schedule": datetime.timedelta(minutes=2),
    },
    "auto_repay_flow": {
        "task": get_celery_task("inspect_auto_repay_flow"),
        "schedule": datetime.timedelta(minutes=8),
    },
}


def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    celery.conf.update(CELERY_TIMEZONE='Asia/Shanghai')
    celery.conf.update(CELERYBEAT_SCHEDULE=CELERYBEAT_SCHEDULE)

    task_base = celery.Task

    class ContextTask(task_base):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return task_base.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery
