from celery import shared_task

import logging

from .models import AdminAccount

logger = logging.getLogger('django')

@shared_task
def process_receive():
    logger.info('checking stellar receive transactions...')
    hotwallet = AdminAccount.objects.get(name='hotwallet')
    hotwallet.process_new_transactions()

@shared_task
def default_task():
    logger.info('running default task')
    return 'True'



