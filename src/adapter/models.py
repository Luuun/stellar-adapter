from logging import getLogger

import requests
from decimal import Decimal
from django.contrib.postgres.fields import JSONField
from django.db import models

from stellar_base.address import Address

from . import settings
from .stellar import to_cents

logger = getLogger('django')


class UserAccount(models.Model):
    user_id = models.CharField(max_length=100, null=True, blank=True)
    account_id = models.CharField(max_length=200, null=True, blank=True)  # Crypto Address
    last_transaction = JSONField(null=True, blank=True, default={})


class AdminAccount(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    account_id = models.CharField(max_length=200, null=True, blank=True)  # Crypto Address
    last_transaction = JSONField(null=True, blank=True, default={})

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
            transactions = address.payments(cursor=cursor)['_embedded']['records']
            print(transactions)
            for i, tx in enumerate(transactions):
                if tx.get('to') != self.account_id:
                    transactions.pop(i)  # remove sends

        else:
            transactions = address.payments()['_embedded']['records']
            for i, tx in enumerate(transactions):
                if tx.get('from') == self.account_id:
                    transactions.pop(i)  # remove sends

        return transactions

    def process_new_transactions(self):
        new_transactions = self.get_new_receive_transactions()
        for tx in new_transactions:
            # Get memo:
            details = requests.get(url=tx['_links']['transaction']['href']).json()
            memo = details.get('memo')
            print('memo: '+str(memo))
            if memo:
                account_id = memo + '*rehive.com'
                user_account = UserAccount.objects.get(account_id=account_id)
                user_email = user_account.user_id  # for this implementation, user_id is the user's email
                amount = to_cents(Decimal(tx['amount']), 7)
                # TODO: replace this with handle function for retries:

                create_rehive_receive(recipient=user_email,
                                      amount=amount,
                                      currency='XLM',
                                      metadata={'type': 'stellar'})

                return True


def create_rehive_receive(recipient, amount, currency, metadata):
    url = getattr(settings, 'REHIVE_API_URL') + '/admin/transactions/receive/'
    headers = {'Authorization': 'Token ' + getattr(settings, 'REHIVE_API_TOKEN')}
    res = requests.post(url,
                        json={'recipient': recipient,
                              'amount': amount,
                              'currency': currency,
                              'metadata': metadata},
                        headers=headers)
    print(res.json())
    return res


class Asset(models.Model):
    code = models.CharField(max_length=12, null=True, blank=True)
    issuer = models.CharField(max_length=200, null=True, blank=True)
    metadata = JSONField(null=False, blank=True, default={})




