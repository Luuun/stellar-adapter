from logging import getLogger

import requests
from decimal import Decimal
from django.contrib.postgres.fields import JSONField
from django.db import models

from stellar_base.address import Address

from . import settings
from .stellar import to_cents

logger = getLogger('django')

STELLAR_WALLET_DOMAIN = 'luuun.com'


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


# Log of all transactions processed:
class Transaction(models.Model):
    STATUS = (
        ('Pending', 'Pending'),
        ('Complete', 'Complete'),
    )
    TYPE = (
        ('send', 'Send'),
        ('receive', 'Receive'),
    )
    code = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    type = models.CharField(max_length=50, choices=TYPE, null=False, blank=False, db_index=True)
    from_reference = models.CharField(max_length=100, null=True, blank=True)
    to_reference = models.CharField(max_length=100, null=True, blank=True)
    data = JSONField(null=True, blank=True, default={})
    amount = MoneyField(default=Decimal(0))
    user_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=24, choices=STATUS, null=True, blank=True, db_index=True)
    server_json = JSONField(null=True, blank=True, default={})  # Store request/response from server.
    metadata = JSONField(null=True, blank=True, default={})


# Log of all receive transactions processed.
class ReceiveTransaction(models.Model):
    STATUS = (
        ('Pending', 'Pending'),
        ('Complete', 'Complete'),
    )
    user_account = models.ForeignKey(UserAccount)
    code = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    recipient = models.CharField(max_length=200, null=True, blank=True)
    amount = MoneyField(default=Decimal(0))
    currency = models.CharField(max_length=200, null=True, blank=True)
    issuer = models.CharField(max_length=200, null=True, blank=True)
    server_response = JSONField(null=True, blank=True, default={})
    status = models.CharField(max_length=24, choices=STATUS, null=True, blank=True, db_index=True)
    data = JSONField(null=True, blank=True, default={})
    metadata = JSONField(null=True, blank=True, default={})


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
    code = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    recipient = models.CharField(max_length=200, null=True, blank=True)
    amount = MoneyField(default=Decimal(0))
    currency = models.CharField(max_length=200, null=True, blank=True)
    issuer = models.CharField(max_length=200, null=True, blank=True)
    server_request = JSONField(null=True, blank=True, default={})
    data = JSONField(null=True, blank=True, default={})
    metadata = JSONField(null=True, blank=True, default={})


# HotWallet/ Operational Accounts for sending or receiving
class AdminAccount(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    account_id = models.CharField(max_length=200, null=True, blank=True)  # Crypto Address
    last_transaction = JSONField(null=True, blank=True, default={})
    network = models.CharField(max_length=100, null=True, blank=True)  # e.g. 'testnet'
    default = models.BooleanField(default=False)

    # TODO: move send_transaction() to here.

    def get_new_receive_transactions(self):
        if not self.last_transaction:
            new_transactions = self.get_receive_transactions()
        else:
            new_transactions = self.get_receive_transactions(cursor=int(self.last_transaction['paging_token']) + 1)

        if new_transactions:
            self.last_transaction = new_transactions[-1]
            self.save()

        return new_transactions

    def get_receive_transactions(self, cursor=None):
        address = Address(address=self.account_id,
                          network=getattr(settings, 'STELLAR_NETWORK'))
        if cursor:
            transactions = address.payments(cursor=cursor, limit=100)['_embedded']['records']
            print(transactions)
            for i, tx in enumerate(transactions):
                if tx.get('to') != self.account_id:
                    transactions.pop(i)  # remove sends

        else:
            transactions = address.payments(limit=100)['_embedded']['records']
            for i, tx in enumerate(transactions):
                if tx.get('to') != self.account_id:
                    transactions.pop(i)  # remove sends

        return transactions

    def process_new_transactions(self):
        new_transactions = self.get_new_receive_transactions()
        for tx in new_transactions:
            # Get memo:
            details = requests.get(url=tx['_links']['transaction']['href']).json()
            memo = details.get('memo')
            print('memo: '+str(memo))

            # TODO: record-keeping of transactions without memos.
            if memo:
                account_id = memo + '*' + STELLAR_WALLET_DOMAIN
                user_account = UserAccount.objects.get(account_id=account_id)
                user_email = user_account.user_id  # for this implementation, user_id is the user's email
                amount = to_cents(Decimal(tx['amount']), 7)

                if tx['asset_type'] == 'native':
                    currency = 'XLM'
                    issuer = ''
                else:
                    currency = tx['asset_code']
                    issuer_address = tx['asset_issuer']
                    issuer = Asset.objects.get(account_id=issuer_address, code=currency).issuer

                # TODO: replace this with handle function for retries:

                # NB -----------------------------------------------------------------------------
                #
                # Should this not create a new send transaction? Not sure how we will handle this?
                # This is not something I considered  when planning the tx model
                #
                # NB -----------------------------------------------------------------------------

                create_rehive_receive(recipient=user_email,
                                      amount=amount,
                                      currency=currency,
                                      issuer=issuer,
                                      metadata={'type': 'stellar'})

                return True


def create_rehive_receive(recipient, amount, currency, issuer, metadata):
    url = getattr(settings, 'REHIVE_API_URL') + '/admin/transactions/receive/'
    headers = {'Authorization': 'Token ' + getattr(settings, 'REHIVE_API_TOKEN')}
    print(headers)
    res = requests.post(url,
                        json={'recipient': recipient,
                              'amount': amount,
                              'currency': currency,
                              'issuer': issuer,
                              'metadata': metadata},
                        headers=headers)
    print(res.json())
    return res


class Asset(models.Model):
    code = models.CharField(max_length=12, null=True, blank=True)
    issuer = models.CharField(max_length=200, null=True, blank=True)
    account_id = models.CharField(max_length=200, null=True, blank=True)
    metadata = JSONField(null=False, blank=True, default={})




