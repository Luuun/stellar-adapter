import json
import os
from collections import OrderedDict

import requests

from celery import shared_task

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.exceptions import APIException, ParseError, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status, exceptions
from rest_framework.generics import GenericAPIView
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from . import settings
from .exceptions import PlatformRequestFailedError, NotImplementedAPIError
from .models import UserAccount, Asset
from .serializers import PurchaseSerializer, WithdrawSerializer, DepositSerializer, \
    SendSerializer, UserAccountSerializer, AddAssetSerializer
from .permissions import AdapterPurchasePermission, AdapterWithdrawPermission, \
    AdapterDepositPermission, AdapterSendPermission, AdapterPermission

from logging import getLogger

from .stellar import create_transaction, get_balance, create_qr_code_url, from_cents, trust_issuer
from .throttling import NoThrottling

logger = getLogger('django')


@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def stellar_adapter_root(request, format=None):
    """
    ### Notes:

    To make use of this adapter:

    1) Set the Rehive webhooks for each tx type to match their corresponding endpoints below.

    2) Set a secret key for each transaction webhook

    3) Ensure the the required ENV variables have been added to the server.

    **Required ENV variables:**

    In order to use the Stellar adapter you must set the following ENV variables on the server.

    `STELLAR_SEND_PRIVATE_KEY` : Private key for adapter sends.
    `STELLAR_SEND_ADDRESS` : Address for adapter sends.
    'STELLAR_RECEIVE_ADDRESS' : Address for adapter receives.
    `STELLAR_NETWORK` : Specifies whether to use the TESTNET or PUBLIC network.
    `REHIVE_API_URL` : Platform URL, used to update transactions on Rehive (eg. 'http://localhost:8080').
    `REHIVE_API_TOKEN` : Token used for Rehive Admin API endpoint when updating transactions.
    `STELLAR_WITHDRAW_SECRET_KEY` : Withdraw Webhook security key (Defaults to 'secret').
    `STELLAR_DEPOSIT_SECRET_KEY` : Deposit Webhook security key (Defaults to 'secret').
    `STELLAR_SEND_SECRET_KEY` : Send Webhook security key (Defaults to 'secret').

    ---

    """

    return Response({'Purchase': reverse('stellar-adapter:purchase',
                                      request=request,
                                      format=format),
                     'Withdraw': reverse('stellar-adapter:withdraw',
                                       request=request,
                                       format=format),
                     'Deposit': reverse('stellar-adapter:deposit',
                                      request=request,
                                      format=format),
                     'Send': reverse('stellar-adapter:send',
                                          request=request,
                                          format=format),
                     })


class PurchaseView(GenericAPIView):
    allowed_methods = ('POST',)
    throttle_classes = (NoThrottling,)
    serializer_class = PurchaseSerializer
    permission_classes = (AdapterPurchasePermission,)

    def post(self, request, *args, **kwargs):
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed('GET')


class WithdrawView(GenericAPIView):
    allowed_methods = ('POST',)
    throttle_classes = (NoThrottling,)
    serializer_class = WithdrawSerializer
    permission_classes = (AdapterWithdrawPermission,)

    def post(self, request, *args, **kwargs):
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed('GET')


class DepositView(GenericAPIView):
    allowed_methods = ('POST',)
    throttle_classes = (NoThrottling,)
    serializer_class = DepositSerializer
    permission_classes = (AdapterDepositPermission,)

    def post(self, request, *args, **kwargs):
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed('GET')


class SendView(GenericAPIView):
    allowed_methods = ('POST',)
    throttle_classes = (NoThrottling,)
    serializer_class = SendSerializer
    permission_classes = (AdapterSendPermission,)

    def post(self, request, *args, **kwargs):
        tx_code = request.data.get('tx_code')
        counterparty = request.data.get('counterparty')
        amount = request.data.get('amount')

        try:
            logger.info('To: ' + counterparty)
            logger.info('Amount: ' + str(amount))
            create_transaction(counterparty, from_cents(amount, 7))
            update_platform_transaction(tx_code, 'Confirmed')
        except Exception as exc:
            update_platform_transaction.delay(tx_code, 'Failed')
            try:
                logger.info(exc.payload)
            except:
                pass
            logger.exception(exc)

        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed('GET')


class BalanceView(APIView):
    allowed_methods = ('GET',)
    throttle_classes = (NoThrottling,)
    permission_classes = (AllowAny,)  # AdapterPermission,)

    def post(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed('POST')

    def get(self, request, *args, **kwargs):
        balance = get_balance()
        return Response({'balance': balance, 'currency': 'XLM'})


class OperatingAccountView(APIView):
    allowed_methods = ('GET',)
    throttle_classes = (NoThrottling,)
    permission_classes = (AllowAny,)  # AdapterPermission,)

    def post(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed('POST')

    def get(self, request, *args, **kwargs):
        address = getattr(settings, 'STELLAR_SEND_ADDRESS')
        qr_code = create_qr_code_url('stellar:'+str(address))
        return Response({'address': address, 'qr_code': qr_code})


class UserAccountView(GenericAPIView):
    allowed_methods = ('POST',)
    throttle_classes = (NoThrottling,)
    permission_classes = (AllowAny,)  # AdapterPermission,) #TODO: re-enable
    serializer_class = UserAccountSerializer

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        # Check if metadata is specified
        if request.data.get('metadata'):
            if type(request.data.get('metadata')) is str:
                metadata = json.loads(request.data.get('metadata'))
            else:
                metadata = request.data.get('metadata')
        else:
            metadata = json.loads('{}')
        account_id = metadata['username'] + '*rehive.com'
        account, created = UserAccount.objects.get_or_create(user_id=user_id, account_id=account_id)
        return Response(OrderedDict([('account_id', account_id),
                                     ('user_id', user_id)]))

    def get(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed('GET')


class StellarFederationView(APIView):
    allowed_methods = ('GET',)
    throttle_classes = (NoThrottling,)
    permission_classes = (AllowAny,)  # AdapterPermission,) #TODO: re-enable

    def post(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed('POST')

    def get(self, request, *args, **kwargs):
        if request.query_params.get('type') == 'name':
            address = request.query_params.get('q')
            if address:
                account_id = address
                operating_receive_address = getattr(settings, 'STELLAR_RECEIVE_ADDRESS')
                if UserAccount.objects.filter(account_id=account_id):
                    return Response(OrderedDict([('stellar_address', address),
                                                 ('account_id', operating_receive_address),
                                                 ('memo_type', 'text'),
                                                 ('memo', address.split('*')[0])]))
                else:
                    raise ValidationError('Stellar address does not exist.')
            else:
                raise ParseError('Invalid query parameter provided.')
        else:
            raise NotImplementedAPIError()


@shared_task(bind=True, name='adapter.update_platform_tx.task', max_retries=24, default_retry_delay=60 * 60)
def update_platform_transaction(self, tx_code, status):
    logger.info('Make transaction update request.')

    # Update URL
    url = getattr(settings, 'REHIVE_API_URL') + '/admin/transactions/update/'

    # Add Authorization headers
    headers = {'Authorization': 'Token ' + getattr(settings, 'REHIVE_API_TOKEN')}

    try:
        # Make request
        r = requests.post(url, json={'tx_code': tx_code, 'status': status}, headers=headers)

        if r.status_code == 200:
            pass
        else:
            logger.info(headers)
            logger.info('Failed transaction update request: HTTP %s Error: %s' % (r.status_code, r.text))

    except (requests.exceptions.RequestException, requests.exceptions.MissingSchema) as e:
        try:
            logger.info('Retry transaction update request due to connection error.')
            self.retry(countdown=5 * 60, exc=PlatformRequestFailedError)
        except PlatformRequestFailedError:
            logger.info('Final transaction update request failure due to connection error.')


class AddAssetView(GenericAPIView):
    allowed_methods = ('POST',)
    throttle_classes = (NoThrottling,)
    permission_classes = (AllowAny,)  # AdapterPermission,) #TODO: re-enable
    serializer_class = AddAssetSerializer

    def post(self, request, *args, **kwargs):
        asset_code = request.data.get('code')
        issuer = request.data.get('issuer')
        # Check if metadata is specified
        if request.data.get('metadata'):
            if type(request.data.get('metadata')) is str:
                metadata = json.loads(request.data.get('metadata'))
            else:
                metadata = request.data.get('metadata')
        else:
            metadata = json.loads('{}')
        try:
            trust_issuer(asset_code, issuer)
            Asset.objects.get_or_create(code=asset_code, issuer=issuer, metadata=metadata)
        except Exception as exc:
            logger.exception(exc)
            try:
                logger.info(exc.payload)
            except:
                pass
            raise APIException('Error adding asset.')

        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed('GET')
