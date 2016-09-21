import urllib.parse

import requests
from stellar_base.builder import Builder, Decimal
from stellar_base.exceptions import APIException

from . import settings
import toml


# Create send transaction in adapter service
from stellar_base.address import Address

from .exceptions import NotImplementedAPIError


def get_federation_details(address):
    if '*' not in address:
        raise TypeError('Invalid federation address')
    user_id, domain = address.split('*')
    stellar_toml = requests.get('https://'+domain+'/.well-known/stellar.toml')
    url = toml.loads(stellar_toml.text)['FEDERATION_SERVER']
    params = {'type': 'name',
              'q': address}
    federation = requests.get(url=url, params=params).json()
    return federation


def create_transaction(counterparty: str, amount: Decimal):
    builder = Builder(secret=getattr(settings, 'STELLAR_SEND_PRIVATE_KEY'),
                      network=getattr(settings, 'STELLAR_NETWORK'))
    if is_valid_address(counterparty):
        address = counterparty
    else:
        federation = get_federation_details(counterparty)
        if federation['memo_type'] == 'text':
            builder.add_text_memo(federation['memo'])
        elif federation['memo_type'] == 'id':
            builder.add_id_memo(federation['memo'])
        elif federation['memo_type'] == 'hash':
            builder.add_hash_memo(federation['memo'])
        else:
            raise NotImplementedAPIError('Invalid memo type specified.')

        address = federation['account_id']

    # Create account or create payment:
    try:
        address_obj = Address(address, network=getattr(settings, 'STELLAR_NETWORK'))
        address_obj.get()
        builder.append_payment_op(address, amount, 'XLM')
    except APIException as exc:
        if exc.status_code == 404:
            builder.append_create_account_op(address, amount)

    try:
        builder.sign()
        builder.submit()
    except Exception as exc:
        print(exc.payload)


def get_balance():

    address = Address(address=getattr(settings, 'STELLAR_SEND_ADDRESS'),
                      network=getattr(settings, 'STELLAR_NETWORK'))

    address.get()
    for balance in address.balances:
        if balance['asset_type'] == 'native':
            return to_cents(Decimal(balance['balance']), 7)


def to_cents(amount: Decimal, divisibility: int) -> int:
    return int(amount * Decimal('10')**Decimal(divisibility))


def from_cents(amount: int, divisibility: int) -> Decimal:
    return Decimal(amount) / Decimal('10')**Decimal(divisibility)


def create_qr_code_url(value, size=300):
    url = "https://chart.googleapis.com/chart?%s" % urllib.parse.urlencode({'chs': size,
                                                                            'cht': 'qr',
                                                                            'chl': value,
                                                                            'choe': 'UTF-8'})

    return url


def get_transactions(cursor=None):
    address = Address(address=getattr(settings, 'STELLAR_SEND_ADDRESS'))
    if cursor:
        return address.payments(cursor=cursor)
    else:
        return address.payments()


def is_valid_address(address: str) -> bool:
    # TODO: Replace with real address check.
    if len(address) == 56 and '*' not in address:
        return True
    else:
        return False


def get_anchor_address(domain, code):
    stellar_toml = requests.get('https://' + domain + '/.well-known/stellar.toml')
    currencies = toml.loads(stellar_toml.text)['CURRENCIES']

    for currency in currencies:
        if currency['code'] == code:
            return currency['issuer']


def trust_issuer(asset_code, issuer):
    builder = Builder(secret=getattr(settings, 'STELLAR_SEND_PRIVATE_KEY'),
                      network=getattr(settings, 'STELLAR_NETWORK'))

    if is_valid_address(issuer):
        address = issuer
    else:
        if '*' in issuer:
            address = get_federation_details(issuer)['account_id']
        else:  # assume it is an anchor domain
            address = get_anchor_address(issuer, asset_code)

    builder.append_trust_op(address, asset_code)

    try:
        builder.sign()
        builder.submit()
    except Exception as exc:
        print(exc.payload)



