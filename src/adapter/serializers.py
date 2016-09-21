from decimal import Decimal

from rest_framework import serializers

from logging import getLogger

logger = getLogger('django')


class PurchaseSerializer(serializers.Serializer):
    tx_code = serializers.CharField(required=True)
    tx_type = serializers.CharField(required=True)
    user = serializers.CharField(required=True)
    counterparty = serializers.CharField(required=False)
    status = serializers.CharField(required=True)
    amount = serializers.CharField(required=True)
    fee = serializers.CharField(required=False)
    currency = serializers.CharField(required=True)
    company = serializers.CharField(required=True)
    created = serializers.CharField(required=True)
    note = serializers.CharField(required=False)
    metadata = serializers.JSONField(required=False)


class WithdrawSerializer(serializers.Serializer):
    tx_code = serializers.CharField(required=True)
    tx_type = serializers.CharField(required=True)
    user = serializers.CharField(required=True)
    counterparty = serializers.CharField(required=False)
    status = serializers.CharField(required=True)
    amount = serializers.CharField(required=True)
    fee = serializers.CharField(required=False)
    currency = serializers.CharField(required=True)
    reference = serializers.JSONField(required=True)
    company = serializers.CharField(required=True)
    created = serializers.CharField(required=True)
    note = serializers.CharField(required=False)
    metadata = serializers.JSONField(required=False)


class DepositSerializer(serializers.Serializer):
    tx_code = serializers.CharField(required=True)
    tx_type = serializers.CharField(required=True)
    user = serializers.CharField(required=True)
    counterparty = serializers.CharField(required=False)
    status = serializers.CharField(required=True)
    amount = serializers.CharField(required=True)
    fee = serializers.CharField(required=False)
    currency = serializers.CharField(required=True)
    company = serializers.CharField(required=True)
    created = serializers.CharField(required=True)
    note = serializers.CharField(required=False)
    metadata = serializers.JSONField(required=False)


class SendSerializer(serializers.Serializer):
    tx_code = serializers.CharField(required=True)
    tx_type = serializers.CharField(required=True)
    user = serializers.CharField(required=True)
    counterparty = serializers.CharField(required=True)
    status = serializers.CharField(required=True)
    amount = serializers.CharField(required=True)
    fee = serializers.CharField(required=False)
    currency = serializers.CharField(required=True)
    company = serializers.CharField(required=True)
    created = serializers.CharField(required=True)
    note = serializers.CharField(required=False)
    metadata = serializers.JSONField(required=False)


class UserAccountSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)
    metadata = serializers.JSONField(required=False)


class AddAssetSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    issuer = serializers.CharField(required=True)
    metadata = serializers.JSONField(required=False)