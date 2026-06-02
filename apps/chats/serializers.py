from rest_framework import serializers

from .intent_constants import (
    INTENT_TRANSACTION_BATCH,
    NON_TRANSACTION_INTENTS,
    REJECTED_ACTION_REASONS,
    UNKNOWN_REASONS,
)
from apps.transactions.serializers import TransactionResponseSerializer


class ChatParseRequestSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False, trim_whitespace=True)


class ChatActionSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["record_transaction"])
    category_id = serializers.UUIDField()
    type = serializers.ChoiceField(choices=["expense", "income"])
    amount = serializers.IntegerField(min_value=1)
    description = serializers.CharField(allow_blank=False)
    transaction_date = serializers.DateField()
    time_inferred = serializers.BooleanField()
    confidence = serializers.FloatField(min_value=0.0, max_value=1.0)


class ChatRejectedActionSerializer(serializers.Serializer):
    raw_text = serializers.CharField(allow_blank=False)
    reason = serializers.ChoiceField(choices=REJECTED_ACTION_REASONS)


class ChatTransactionBatchResultSerializer(serializers.Serializer):
    intent = serializers.ChoiceField(choices=[INTENT_TRANSACTION_BATCH])
    actions = ChatActionSerializer(many=True)
    rejected_actions = ChatRejectedActionSerializer(many=True, required=False)


class ChatNonTransactionResultSerializer(serializers.Serializer):
    intent = serializers.ChoiceField(choices=NON_TRANSACTION_INTENTS)
    reason = serializers.ChoiceField(choices=UNKNOWN_REASONS, required=False)


class ChatParseResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = serializers.JSONField()


class QueryResultSerializer(serializers.Serializer):
    columns = serializers.ListField(child=serializers.CharField())
    rows = serializers.ListField(child=serializers.ListField())
    sql = serializers.CharField(required=False, allow_blank=True)


class ChatParseCommitResultSerializer(serializers.Serializer):
    message = serializers.CharField()
    created_transactions = TransactionResponseSerializer(many=True)
    query_result = QueryResultSerializer(required=False, allow_null=True)


class ChatParseCommitResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = ChatParseCommitResultSerializer()


class ChatParseLLMResponseResultSerializer(serializers.Serializer):
    message = serializers.CharField()


class ChatParseLLMResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = ChatParseLLMResponseResultSerializer()


class ChatMessageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    sender = serializers.CharField()
    content = serializers.CharField()
    created_at = serializers.DateTimeField()


class ChatDeleteHistoryResultSerializer(serializers.Serializer):
    message = serializers.CharField()
    deleted = serializers.IntegerField()


class ChatDeleteHistoryResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = ChatDeleteHistoryResultSerializer()
