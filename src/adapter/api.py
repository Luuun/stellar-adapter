from logging import getLogger
from decimal import Decimal

import requests
from django.conf import settings
from stellar_base.address import Address
from stellar_base.builder import Builder
from stellar_base.exceptions import APIException

from .exceptions import NotImplementedAPIError
from .stellar_federation import get_federation_details, address_from_domain
from .utils import to_cents, create_qr_code_url
from.models import ReceiveTransaction, UserAccount, Asset

logger = getLogger('django')


class Interface:
    """
    Interface to handle all API calls to third-party account.
    """
    def __init__(self, account):
        self.account = account
        if account.secret:
            self.builder = Builder(secret=account.secret,
                                   network=account.network)
        self.address = Address(address=account.account_id,
                               network=account.network)

    def _get_new_receives(self):
        # Get all stored transactions for account
        transactions = ReceiveTransaction.filter(admin_account=self.account)

        # Set the cursor according to latest stored transaction:
        if not transactions:
            cursor = None
        else:
            cursor = int(transactions.latest().data['paging_token']) + 1

        # Get new transactions from the stellar network:
        new_transactions = self._get_receives(cursor=cursor)

        return new_transactions

    def _get_receives(self, cursor=None):
        # If cursor was specified, get all transactions after the cursor:
        if cursor:
            transactions = self.address.payments(cursor=cursor)['_embedded']['records']
            print(transactions)
            for i, tx in enumerate(transactions):
                if tx.get('to') != self.account.account_id:
                    transactions.pop(i)  # remove sends

        # else just get all the transactions:
        else:
            transactions = self.address.payments()['_embedded']['records']
            for i, tx in enumerate(transactions):
                if tx.get('from') == self.account.account_id:
                    transactions.pop(i)  # remove sends

        return transactions

    def _process_receive(self, tx):
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

    @staticmethod
    def _is_valid_address(address: str) -> bool:
        # TODO: Replace with real address check.
        if len(address) == 56 and '*' not in address:
            return True
        else:
            return False

    # This function should always be included if transactions are received to admin account and not added via webhooks:
    def process_receives(self):
        # Get new receive transactions
        new_transactions = self._get_new_receives()

        # Add each transaction to Rehive and log in transaction table:
        for tx in new_transactions:
            self._process_receive(tx)

    # This function should always be included.
    def process_send(self, tx):
        if self._is_valid_address(tx.recipient):
            address = tx.recipient
        else:
            federation = get_federation_details(tx.recipient)
            if federation['memo_type'] == 'text':
                self.builder.add_text_memo(federation['memo'])
            elif federation['memo_type'] == 'id':
                self.builder.add_id_memo(federation['memo'])
            elif federation['memo_type'] == 'hash':
                self.builder.add_hash_memo(federation['memo'])
            else:
                raise NotImplementedAPIError('Invalid memo type specified.')

            address = federation['account_id']

        # Create account or create payment:
        if tx.currency == 'XLM':
            try:
                address_obj = self.address
                address_obj.get()
                self.builder.append_payment_op(address, tx.amount, 'XLM')
            except APIException as exc:
                if exc.status_code == 404:
                    self.builder.append_create_account_op(address, tx.amount)
        else:
            # Get issuer address details:
            issuer_address = get_issuer_address(tx.issuer, tx.currency)

            address_obj = self.address
            address_obj.get()
            self.builder.append_payment_op(address, tx.amount, tx.currency, issuer_address)

        try:
            self.builder.sign()
            self.builder.submit()
        except Exception as exc:
            print(exc.payload)

    def get_balance(self):
        address = self.address
        address.get()
        for balance in address.balances:
            if balance['asset_type'] == 'native':
                return to_cents(Decimal(balance['balance']), 7)

    def get_issuer_address(self, issuer, asset_code):
        if self._is_valid_address(issuer):
            address = issuer
        else:
            if '*' in issuer:
                address = get_federation_details(issuer)['account_id']
            else:  # assume it is an anchor domain
                address = address_from_domain(issuer, asset_code)

        return address

    def trust_issuer(self, asset_code, issuer):
        logger.info('Trusting issuer: %s %s' % (issuer, asset_code))
        address = self.get_issuer_address(issuer, asset_code)
        self.builder.append_trust_op(address, asset_code)

        try:
            self.builder.sign()
            self.builder.submit()
        except Exception as exc:
            print(exc.payload)

    # Generate new crypto address/ account id
    @staticmethod
    def new_account_id(**kwargs):
        metadata = kwargs.get('metadata')
        account_id = metadata['username'] + '*' + getattr(settings, 'STELLAR_WALLET_DOMAIN')
        return account_id

    def get_account_details(self):
        address = self.account.account_id
        qr_code = create_qr_code_url('stellar:' + str(address))
        return {'account_id': address, 'metadata': {'qr_code': qr_code}}


