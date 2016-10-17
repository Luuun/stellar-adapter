import urllib.parse
from logging import getLogger

import requests
from stellar_base.builder import Builder, Decimal
from stellar_base.exceptions import APIException

from stellar_adapter import settings
import toml

logger = getLogger('django')

# Create send transaction in adapter service
from stellar_base.address import Address

from stellar_adapter.exceptions import NotImplementedAPIError


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


def create_transaction(counterparty: str, amount: Decimal, currency='XLM', issuer=None):
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
    if currency == 'XLM':
        try:
            address_obj = Address(address, network=getattr(settings, 'STELLAR_NETWORK'))
            address_obj.get()
            builder.append_payment_op(address, amount, 'XLM')
        except APIException as exc:
            if exc.status_code == 404:
                builder.append_create_account_op(address, amount)
    else:
        # Get issuer address details:
        issuer_address = get_issuer_address(issuer, currency)

        address_obj = Address(address, network=getattr(settings, 'STELLAR_NETWORK'))
        address_obj.get()
        builder.append_payment_op(address, amount, currency, issuer_address)

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


def address_from_domain(domain, code):
    logger.info('Fetching address from domain.')
    stellar_toml = requests.get('https://' + domain + '/.well-known/stellar.toml')
    currencies = toml.loads(stellar_toml.text)['CURRENCIES']

    for currency in currencies:
        if currency['code'] == code:
            logger.info('Address: %s' % (currency['issuer'],))
            return currency['issuer']


def get_issuer_address(issuer, asset_code):
    if is_valid_address(issuer):
        address = issuer
    else:
        if '*' in issuer:
            address = get_federation_details(issuer)['account_id']
        else:  # assume it is an anchor domain
            address = address_from_domain(issuer, asset_code)

    return address


def trust_issuer(asset_code, issuer):
    logger.info('Trusting issuer: %s %s' % (issuer, asset_code))
    builder = Builder(secret=getattr(settings, 'STELLAR_SEND_PRIVATE_KEY'),
                      network=getattr(settings, 'STELLAR_NETWORK'))

    address = get_issuer_address(issuer, asset_code)

    builder.append_trust_op(address, asset_code)

    try:
        builder.sign()
        builder.submit()
    except Exception as exc:
        print(exc.payload)



