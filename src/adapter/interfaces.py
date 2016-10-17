from datetime import datetime, timedelta
from logging import getLogger
from decimal import Decimal
from django.utils.timezone import utc

from .models import AdminAccount

logger = getLogger('django')


class Interface:
    """
    Interface to handle all API calls to third-party account.
    """

    def __init__(self, account):
        self.account = account

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
            print('memo: ' + str(memo))
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



class APICallError(Exception):
    # Exception thrown when trying
    # API call fails
    pass


class ExchangeInitializationError(Exception):
    # Exception thrown when trying
    # to initialise exchange
    pass


class APIDataOutdatedError(Exception):
    # Exception thrown when
    # API data is outdated
    pass
