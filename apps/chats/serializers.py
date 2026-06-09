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


class AdminAIRequestQuerySerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=["success", "failed", "partial", "error"], required=False
    )
    intent = serializers.ChoiceField(
        choices=["transaction_batch", "financial_question", "greeting", "unknown"],
        required=False,
    )
    model = serializers.CharField(required=False, allow_blank=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)


class AdminAIOverviewSerializer(serializers.Serializer):
    total_requests = serializers.IntegerField()
    success_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    partial_count = serializers.IntegerField()
    success_rate = serializers.FloatField()
    avg_latency_ms = serializers.FloatField()
    p95_latency_ms = serializers.IntegerField()
    intent_distribution = serializers.DictField(
        child=serializers.IntegerField(), default={}
    )


class AdminAIOverviewResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = AdminAIOverviewSerializer()


class AdminAIRequestListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    user_email = serializers.EmailField()
    user_message = serializers.CharField(allow_null=True, required=False)
    assistant_message = serializers.CharField()
    intent = serializers.CharField(allow_null=True, required=False)
    status = serializers.CharField(allow_null=True, required=False)
    model = serializers.CharField(allow_null=True, required=False)
    latency_ms = serializers.IntegerField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()


class AdminAIRequestDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    user_email = serializers.EmailField()
    user_message = serializers.CharField(allow_null=True, required=False)
    assistant_message = serializers.CharField()
    metadata = serializers.JSONField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()


class AdminAIRequestDetailResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = AdminAIRequestDetailSerializer()


class AdminAIRequestDeleteResultSerializer(serializers.Serializer):
    message = serializers.CharField()
    deleted = serializers.IntegerField()
    purge_after = serializers.DateTimeField()


class AdminAIRequestDeleteResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=1000)
    result = AdminAIRequestDeleteResultSerializer()


class AdminAIErrorItemSerializer(serializers.Serializer):
    error_type = serializers.CharField()
    message = serializers.CharField()
    count = serializers.IntegerField()
    last_seen_at = serializers.DateTimeField()
