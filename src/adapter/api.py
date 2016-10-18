from logging import getLogger
from decimal import Decimal

import requests
from django.conf import settings
from stellar_base.address import Address

from src.adapter.utils import to_cents
from.models import ReceiveTransaction, UserAccount, Asset

logger = getLogger('django')


class Interface:
    """
    Interface to handle all API calls to third-party account.
    """

    def __init__(self, account):
        self.account = account

    def _get_new_receive_transactions(self):
        # Get all stored transactions for account
        transactions = ReceiveTransaction.filter(admin_account=self.account)

        # Set the cursor according to latest stored transaction:
        if not transactions:
            cursor = None
        else:
            cursor = int(transactions.latest().data['paging_token']) + 1

        # Get new transactions from the stellar network:
        new_transactions = self._get_receive_transactions(cursor=cursor)

        return new_transactions

    def _get_receive_transactions(self, cursor=None):
        address = Address(address=self.account.account_id,
                          network=getattr(settings, self.account.network))

        # If cursor was specified, get all transactions after the cursor:
        if cursor:
            transactions = address.payments(cursor=cursor)['_embedded']['records']
            print(transactions)
            for i, tx in enumerate(transactions):
                if tx.get('to') != self.account.account_id:
                    transactions.pop(i)  # remove sends

        # else just get all the transactions:
        else:
            transactions = address.payments()['_embedded']['records']
            for i, tx in enumerate(transactions):
                if tx.get('from') == self.account.account_id:
                    transactions.pop(i)  # remove sends

        return transactions

    def _process_new_transaction(self, tx):
        # Get memo:
        details = requests.get(url=tx['_links']['transaction']['href']).json()
        memo = details.get('memo')
        print('memo: ' + str(memo))
        if memo:
            account_id = memo + '*rehive.com'
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

            # Create Transaction:
            tx = ReceiveTransaction.objects.create(user_account=user_account,
                                                   external_id=tx['hash'],
                                                   recipient=user_email,
                                                   amount=amount,
                                                   currency=currency,
                                                   issuer=issuer,
                                                   status='Waiting',
                                                   data=tx,
                                                   metadata={'type': 'stellar'}
                                                   )

            # TODO: Move tx.upload_to_rehive() to a signal to auto-run after Transaction creation.
            tx.upload_to_rehive()

            return True

    # This function should always be included, unless Transactions are added via webhooks:
    def process_new_transactions(self):
        # Get new receive transactions
        new_transactions = self._get_new_receive_transactions()

        # Add each transaction to Rehive and log in transaction table:
        for tx in new_transactions:
            self._process_new_transaction(tx)
