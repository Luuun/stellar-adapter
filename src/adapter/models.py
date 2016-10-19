from logging import getLogger

from decimal import Decimal
from django.contrib.postgres.fields import JSONField
from django.db import models

from .api import Interface
from .tasks import create_rehive_receive, confirm_rehive_transaction

logger = getLogger('django')


class MoneyField(models.DecimalField):
    """Decimal Field with hardcoded precision of 28 and a scale of 18."""

    def __init__(self, verbose_name=None, name=None, max_digits=28,
                 decimal_places=18, **kwargs):
        super(MoneyField, self).__init__(verbose_name, name, max_digits, decimal_places, **kwargs)


# User accounts for receiving
class UserAccount(models.Model):
    user_id = models.CharField(max_length=100, null=True, blank=True)
    account_id = models.CharField(max_length=200, null=True, blank=True)  # Crypto Address
    last_transaction = JSONField(null=True, blank=True, default={})


# Log of all receive transactions processed.
class ReceiveTransaction(models.Model):
    STATUS = (
        ('Waiting', 'Waiting'),
        ('Pending', 'Pending'),
        ('Complete', 'Complete'),
        ('Failed', 'Failed'),
    )
    user_account = models.ForeignKey(UserAccount)
    external_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    rehive_code = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    recipient = models.CharField(max_length=200, null=True, blank=True)
    amount = MoneyField(default=Decimal(0))
    currency = models.CharField(max_length=200, null=True, blank=True)
    issuer = models.CharField(max_length=200, null=True, blank=True)
    rehive_response = JSONField(null=True, blank=True, default={})
    status = models.CharField(max_length=24, choices=STATUS, null=True, blank=True, db_index=True)
    data = JSONField(null=True, blank=True, default={})
    metadata = JSONField(null=True, blank=True, default={})

    def upload_to_rehive(self):
        if not self.rehive_code:
            if self.status in ['Pending', 'Complete']:
                create_rehive_receive(self.id)
        else:
            if self.status == 'Complete':
                confirm_rehive_transaction(self.id)


# Log of all processed sends.
class SendTransaction(models.Model):
    STATUS = (
        ('Pending', 'Pending'),
        ('Complete', 'Complete'),
    )
    TYPE = (
        ('send', 'Send'),
        ('receive', 'Receive'),
    )
    admin_account = models.ForeignKey(AdminAccount)
    external_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    rehive_code = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    recipient = models.CharField(max_length=200, null=True, blank=True)
    amount = MoneyField(default=Decimal(0))
    currency = models.CharField(max_length=200, null=True, blank=True)
    issuer = models.CharField(max_length=200, null=True, blank=True)
    rehive_request = JSONField(null=True, blank=True, default={})
    data = JSONField(null=True, blank=True, default={})
    metadata = JSONField(null=True, blank=True, default={})

    def execute(self):
        account = AdminAccount.objects.get(default=True)
        account.process_send(self)


# HotWallet/ Operational Accounts for sending or receiving
class AdminAccount(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    secret = models.CharField(max_length=200, null=True, blank=True)  # Crypto seed or private key
    account_id = models.CharField(max_length=200, null=True, blank=True)  # Crypto Address
    network = models.CharField(max_length=100, null=True, blank=True)  # e.g. 'testnet'
    default = models.BooleanField(default=False)

    # For cryptos like stellar where all transactions are received to single account.
    # Alternative to webhooks.
    def process_receive_transactions(self):
        interface = Interface(account=self)
        interface.process_receives()

    def process_send(self, tx):
        interface = Interface(account=self)
        interface.process_send(tx)


# Crypto Asset.
class Asset(models.Model):
    code = models.CharField(max_length=12, null=True, blank=True)
    issuer = models.CharField(max_length=200, null=True, blank=True)
    account_id = models.CharField(max_length=200, null=True, blank=True)
    metadata = JSONField(null=False, blank=True, default={})




