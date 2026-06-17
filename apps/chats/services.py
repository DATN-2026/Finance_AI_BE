import json
import os
import re
from decimal import Decimal
from datetime import datetime, date
from typing import Any
from urllib import error, request

from .prompts import SYSTEM_INSTRUCTION_TEMPLATE, RESPONSE_SYSTEM_INSTRUCTION_TEMPLATE

import sqlparse
from sqlparse.tokens import DDL, DML, Keyword, Punctuation

from django.db import connection, transaction
from django.conf import settings

from apps.categories.selector import list_user_categories
from apps.transactions.services import TransactionServiceError, create_transaction
from apps.users.models import User

from .models import AIChatMessage
from .intent_constants import (
    ALL_INTENTS,
    FINANCIAL_SUBJECT_SCOPES,
    INTENT_FINANCIAL_QUESTION,
    INTENT_GREETING,
    INTENT_TRANSACTION_BATCH,
    INTENT_UNKNOWN,
    REJECTED_ACTION_REASONS,
    SUBJECT_SCOPE_AMBIGUOUS,
    SUBJECT_SCOPE_OTHER_PERSON,
    SUBJECT_SCOPE_SELF,
    UNKNOWN_REASON_OTHER_PERSON,
)

FINANCIAL_OTHER_PERSON_MESSAGE = (
    "I can only answer questions about your own financial data. "
    "I can't access or analyze another person's finances."
)

FINANCIAL_AMBIGUOUS_MESSAGE = (
    "I'm not sure whose financial data you're asking about. "
    "I can only answer questions about your own finances, so please rephrase "
    "the question to make it clear it's about you."
)

_MONEY_PATTERN = re.compile(
    r"(?i)(?:\b\d+(?:[\.,]\d+)?\s*(?:k|tr|trieu|cu|xi|vnd|đ|d)?\b)",
    flags=re.UNICODE,
)

_FINANCIAL_QUESTION_SCOPE_TERMS = (
    "bao nhiêu",
    "bao nhieu",
    "chi tiêu",
    "chi tieu",
    "tiêu",
    "tieu",
    "thu nhập",
    "thu nhap",
    "ngân sách",
    "ngan sach",
    "giao dịch",
    "giao dich",
    "spend",
    "spent",
    "income",
    "budget",
    "transaction",
)

_AMBIGUOUS_FINANCIAL_SCOPE_MARKERS = (
    "với mình",
    "voi minh",
    "với tôi",
    "voi toi",
    "của nhà",
    "cua nha",
    "gia đình",
    "gia dinh",
    "household",
    "shared",
)

_SELF_FINANCIAL_SCOPE_MARKERS = (
    "tôi",
    "toi",
    "mình",
    "minh",
    "của tôi",
    "cua toi",
    "của mình",
    "cua minh",
    "my",
)

_OTHER_PERSON_STARTERS = (
    "mẹ",
    "me",
    "ba",
    "bố",
    "bo",
    "cha",
    "mom",
    "dad",
    "boss",
    "sếp",
    "sep",
)


def _starts_with_third_person_name(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False

    first_token = text.split()[0].strip("\"'“”‘’()[]{}.,;:!?")
    if not first_token:
        return False

    first_person = {
        "tôi",
        "toi",
        "mình",
        "minh",
        "tui",
        "tao",
        "tớ",
        "to",
        "em",
        "anh",
        "chị",
        "i",
        "we",
        "me",
        "my",
    }
    non_name_time = {
        "hôm",
        "hom",
        "nay",
        "today",
        "yesterday",
        "this",
        "last",
        "sáng",
        "sang",
        "trưa",
        "trua",
        "chiều",
        "chieu",
        "tối",
        "toi",
    }

    lowered = first_token.lower()
    if lowered in first_person or lowered in non_name_time:
        return False

    return first_token[:1].isupper()


def _infer_unknown_reason(message: str) -> str | None:
    text = (message or "").strip()
    if not text:
        return None

    if not _MONEY_PATTERN.search(text):
        return None

    if not _starts_with_third_person_name(text):
        return None

    lowered = text.lower()
    transactionish_verbs = (
        "ăn",
        "an",
        "uống",
        "uong",
        "mua",
        "tốn",
        "ton",
        "hết",
        "het",
        "spent",
        "bought",
    )
    if not any(verb in lowered for verb in transactionish_verbs):
        return None

    user_affecting_markers = (
        "tôi trả",
        "mình trả",
        "i paid",
        "i spent",
        "tôi mua",
        "mình mua",
        "trả tôi",
        "paid me",
    )
    if any(marker in lowered for marker in user_affecting_markers):
        return None

    return UNKNOWN_REASON_OTHER_PERSON


def _infer_financial_question_subject_scope(message: str) -> str | None:
    text = (message or "").strip()
    if not text:
        return None

    lowered = text.lower()
    if not any(term in lowered for term in _FINANCIAL_QUESTION_SCOPE_TERMS):
        return None

    if any(marker in lowered for marker in _AMBIGUOUS_FINANCIAL_SCOPE_MARKERS):
        return SUBJECT_SCOPE_AMBIGUOUS

    if any(marker in lowered for marker in _SELF_FINANCIAL_SCOPE_MARKERS):
        return None

    first_token = lowered.split()[0].strip("\"'()[]{}.,;:!?") if lowered.split() else ""
    if _starts_with_third_person_name(text) or first_token in _OTHER_PERSON_STARTERS:
        return SUBJECT_SCOPE_OTHER_PERSON

    return None


def _apply_financial_subject_scope_guard(
    result: dict[str, Any], message: str
) -> dict[str, Any]:
    if result.get("intent") != INTENT_FINANCIAL_QUESTION:
        return result

    inferred_scope = _infer_financial_question_subject_scope(message)
    if inferred_scope in {SUBJECT_SCOPE_OTHER_PERSON, SUBJECT_SCOPE_AMBIGUOUS}:
        result["subject_scope"] = inferred_scope
        result["sql"] = None

    return result


class ChatServiceError(Exception):
    pass


def _build_user_categories_json(user: User) -> list[dict[str, Any]]:
    categories = list_user_categories(user=user)

    def _normalize_uuid(val):
        try:
            return val.hex
        except Exception:
            return str(val).replace("-", "")

    return [
        {
            "id": _normalize_uuid(category.id),
            "name": category.name,
            "type": category.type,
            "aliases": [],
        }
        for category in categories
    ]


def _build_system_instruction(user: User) -> str:
    now = datetime.now()
    user_categories_json = _build_user_categories_json(user=user)
    return SYSTEM_INSTRUCTION_TEMPLATE.format(
        current_datetime_iso=now.isoformat(),
        user_timezone=settings.TIME_ZONE,
        user_categories_json=json.dumps(user_categories_json, ensure_ascii=False),
    )


def _extract_text_from_gemini_response(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        raise ChatServiceError("Gemini returned empty candidates")

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    if not parts:
        raise ChatServiceError("Gemini returned empty content")

    text = parts[0].get("text")
    if not text or not isinstance(text, str):
        raise ChatServiceError("Gemini returned invalid text payload")
    return text


def _call_gemini(
    message: str, system_instruction: str, response_mime_type: str = "application/json"
) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL")
    if not api_key:
        raise ChatServiceError("Missing GEMINI_API_KEY")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": message}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": response_mime_type,
        },
    }

    req = request.Request(
        url=url,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        data=json.dumps(payload).encode("utf-8"),
    )

    try:
        with request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise ChatServiceError(f"Gemini HTTP error: {details}") from exc
    except error.URLError as exc:
        raise ChatServiceError("Gemini connection error") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ChatServiceError("Invalid Gemini response format") from exc

    return _extract_text_from_gemini_response(parsed)


def _validate_action(
    action: dict[str, Any], user_categories: dict[str, str]
) -> dict[str, Any]:
    required_fields = [
        "kind",
        "category_id",
        "type",
        "amount",
        "description",
        "transaction_date",
        "time_inferred",
        "confidence",
    ]
    for field in required_fields:
        if field not in action:
            raise ChatServiceError(f"Missing action field: {field}")

    if action["kind"] != "record_transaction":
        raise ChatServiceError("Invalid action kind")

    category_id = str(action["category_id"])
    if category_id not in user_categories:
        raise ChatServiceError("Invalid category_id in action")

    category_type = user_categories[category_id]
    tx_type = action["type"]
    if tx_type not in {"expense", "income"}:
        raise ChatServiceError("Invalid action type")
    if category_type in {"expense", "income"} and category_type != tx_type:
        raise ChatServiceError("Action type does not match category type")

    amount = action["amount"]
    if not isinstance(amount, int) or amount <= 0:
        raise ChatServiceError("Invalid action amount")

    try:
        datetime.strptime(action["transaction_date"], "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise ChatServiceError("Invalid transaction_date") from exc

    confidence = action["confidence"]
    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
        raise ChatServiceError("Invalid confidence")

    if not isinstance(action["time_inferred"], bool):
        raise ChatServiceError("Invalid time_inferred")

    if not isinstance(action["description"], str) or not action["description"].strip():
        raise ChatServiceError("Invalid description")

    return {
        "kind": action["kind"],
        "category_id": category_id,
        "type": tx_type,
        "amount": amount,
        "description": action["description"].strip(),
        "transaction_date": action["transaction_date"],
        "time_inferred": action["time_inferred"],
        "confidence": float(confidence),
    }


def _validate_llm_output(raw_text: str, user: User) -> dict[str, Any]:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ChatServiceError("LLM output is not valid JSON") from exc

    if not isinstance(data, dict):
        raise ChatServiceError("LLM output must be a JSON object")

    intent = data.get("intent")
    if intent not in ALL_INTENTS:
        raise ChatServiceError("Invalid intent")

    if intent != INTENT_TRANSACTION_BATCH:
        if intent == INTENT_FINANCIAL_QUESTION:
            subject_scope = data.get("subject_scope")
            if subject_scope not in FINANCIAL_SUBJECT_SCOPES:
                raise ChatServiceError("Invalid financial question subject_scope")

            if subject_scope == SUBJECT_SCOPE_SELF:
                sql = data.get("sql")
                if not isinstance(sql, str) or not sql.strip():
                    raise ChatServiceError("Missing SQL for self financial question")

                return {
                    "intent": intent,
                    "subject_scope": subject_scope,
                    "sql": sql.strip(),
                }

            return {
                "intent": intent,
                "subject_scope": subject_scope,
                "sql": None,
            }
        return {"intent": intent}

    actions = data.get("actions")
    if not isinstance(actions, list):
        raise ChatServiceError("actions must be a list for transaction_batch")

    user_categories = {
        str(category.id): category.type for category in list_user_categories(user=user)
    }
    validated_actions = [
        _validate_action(action, user_categories)
        for action in actions
        if isinstance(action, dict)
    ]

    rejected_actions: list[dict[str, str]] = []
    raw_rejected = data.get("rejected_actions", [])
    if raw_rejected is not None:
        if not isinstance(raw_rejected, list):
            raise ChatServiceError("rejected_actions must be a list")
        for item in raw_rejected:
            if not isinstance(item, dict):
                continue
            raw_text = item.get("raw_text")
            reason = item.get("reason")
            if (
                isinstance(raw_text, str)
                and raw_text
                and reason in REJECTED_ACTION_REASONS
            ):
                rejected_actions.append({"raw_text": raw_text, "reason": reason})

    if not validated_actions:
        # Option B: if the model detected transactions but couldn't extract valid actions
        # (e.g. missing amount), still return intent=transaction_batch with rejected_actions.
        if rejected_actions:
            return {
                "intent": INTENT_TRANSACTION_BATCH,
                "actions": [],
                "rejected_actions": rejected_actions,
            }
        return {"intent": INTENT_UNKNOWN}

    result: dict[str, Any] = {
        "intent": INTENT_TRANSACTION_BATCH,
        "actions": validated_actions,
    }
    if rejected_actions:
        result["rejected_actions"] = rejected_actions
    return result


def _build_response_message_llm(parse_result: dict[str, Any]) -> str:
    raw_text = _call_gemini(
        message=json.dumps(parse_result, ensure_ascii=False),
        system_instruction=RESPONSE_SYSTEM_INSTRUCTION_TEMPLATE,
    )
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ChatServiceError("LLM response is not valid JSON") from exc

    if not isinstance(data, dict) or "message" not in data:
        raise ChatServiceError("LLM response missing message")

    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ChatServiceError("LLM response message is invalid")

    return message.strip()


def _build_commit_message(parse_result: dict[str, object], created_count: int) -> str:
    intent = parse_result.get("intent")

    if intent == INTENT_TRANSACTION_BATCH:
        rejected = parse_result.get("rejected_actions") or []
        if created_count > 0:
            if rejected:
                return (
                    f"Recorded {created_count} transaction(s). "
                    "Some items could not be processed due to missing information."
                )
            return f"Successfully recorded {created_count} transaction(s)."

        if rejected:
            return (
                "Unable to record the transaction because some information is missing. "
                "Please complete the details and try again."
            )

        return "The information provided is too vague. Please enter more details."

    if intent == INTENT_UNKNOWN:
        reason = parse_result.get("reason")
        if reason == UNKNOWN_REASON_OTHER_PERSON:
            return (
                "It seems you are referring to a transaction of another person. "
                "If you want to record for yourself, please enter something like: "
                "'I bought...' or 'I paid...'."
            )
        return "The information provided is too vague. Please enter more details."

    if intent == INTENT_FINANCIAL_QUESTION:
        subject_scope = parse_result.get("subject_scope")
        if subject_scope == SUBJECT_SCOPE_OTHER_PERSON:
            return FINANCIAL_OTHER_PERSON_MESSAGE
        if subject_scope == SUBJECT_SCOPE_AMBIGUOUS:
            return FINANCIAL_AMBIGUOUS_MESSAGE
        return "This is a financial question."

    if intent == INTENT_GREETING:
        return "Xin chao! Hay nhap nội dung cần hỗ trợ ."

    return "The information provided is too vague. Please enter more details."


def parse_message(user: User, message: str) -> dict[str, Any]:
    import time

    start_t = time.time()
    started_at = datetime.now()

    system_instruction = _build_system_instruction(user=user)
    raw_llm_output = _call_gemini(
        message=message, system_instruction=system_instruction
    )
    result = _validate_llm_output(raw_text=raw_llm_output, user=user)
    result = _apply_financial_subject_scope_guard(result, message)

    if result.get("intent") == INTENT_UNKNOWN:
        reason = _infer_unknown_reason(message)
        if reason:
            result["reason"] = reason

    finished_at = datetime.now()
    latency_ms = int((time.time() - start_t) * 1000)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    llm_calls = [
        {
            "step": "intent_parsing",
            "model": model_name,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "latency_ms": latency_ms,
        }
    ]

    AIChatMessage.objects.create(
        user=user,
        sender="user",
        content=message,
    )
    AIChatMessage.objects.create(
        user=user,
        sender="assistant",
        content=json.dumps(result, ensure_ascii=False),
        metadata={
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "latency_ms": latency_ms,
            "status": "success",
            "raw_llm_output": raw_llm_output,
            "model": model_name,
            "llm_calls": llm_calls,
        },
    )

    return result


def parse_message_for_commit(
    user: User, message: str
) -> tuple[dict[str, Any], str, str, dict]:
    import time

    start_t = time.time()
    started_at = datetime.now()

    system_instruction = _build_system_instruction(user=user)
    raw_llm_output = _call_gemini(
        message=message, system_instruction=system_instruction
    )
    result = _validate_llm_output(raw_text=raw_llm_output, user=user)
    # result = _apply_financial_subject_scope_guard(result, message)

    if result.get("intent") == INTENT_UNKNOWN:
        reason = _infer_unknown_reason(message)
        if reason:
            result["reason"] = reason

    finished_at = datetime.now()
    latency_ms = int((time.time() - start_t) * 1000)
    model_name = os.getenv("GEMINI_MODEL")

    intent_step_info = {
        "step": "intent_parsing",
        "model": model_name,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "latency_ms": latency_ms,
    }

    return result, raw_llm_output, model_name, intent_step_info


def validate_and_sanitize_sql(sql_str: str, user_id: str) -> str:
    # 1. Check placeholder presence
    if "USER_ID_PLACEHOLDER" not in sql_str:
        raise ValueError("Missing USER_ID_PLACEHOLDER constraint in SQL query.")

    # 2. Parse using sqlparse
    parsed = sqlparse.parse(sql_str)
    if not parsed:
        raise ValueError("Invalid SQL syntax.")

    statement = parsed[0]
    if statement.get_type() != "SELECT":
        raise ValueError("Only SELECT statements are allowed.")

    # 3. Check tokens recursively
    def check_tokens(tokens):
        for token in tokens:
            if token.ttype is Punctuation and token.value == ";":
                raise ValueError("Semicolons are not allowed in the query.")

            if token.ttype in (DML, DDL):
                val = token.value.upper()
                if val not in ("SELECT", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER"):
                    raise ValueError(
                        f"Forbidden DDL/DML keyword detected: {token.value}"
                    )

            if token.ttype is Keyword:
                val = token.value.upper()
                if val in ("INTO", "OUTFILE", "DUMPFILE"):
                    raise ValueError(f"Forbidden keyword: {token.value}")

            if token.is_group:
                check_tokens(token.tokens)

    check_tokens(statement.tokens)

    # 4. Inject limit if not present
    normalized_sql = sql_str.strip().rstrip(";")
    if "LIMIT" not in normalized_sql.upper():
        normalized_sql += " LIMIT 100"

    # 5. Inject MySQL execution time optimizer hint
    if normalized_sql.upper().startswith("SELECT"):
        normalized_sql = re.sub(
            r"^select\b",
            "SELECT /*+ MAX_EXECUTION_TIME(1000) */",
            normalized_sql,
            flags=re.IGNORECASE,
        )

    # 6. Replace placeholder with real user id (supporting both single and double quotes or none)
    sanitized_sql = normalized_sql.replace("'USER_ID_PLACEHOLDER'", f"'{user_id}'")
    sanitized_sql = sanitized_sql.replace('"USER_ID_PLACEHOLDER"', f"'{user_id}'")
    sanitized_sql = sanitized_sql.replace("USER_ID_PLACEHOLDER", f"'{user_id}'")

    return sanitized_sql


def commit_parse_result(
    user: User,
    user_message: str,
    parse_result: dict[str, Any],
    raw_llm_output: str,
    model_name: str,
    intent_step_info: dict = None,
    overall_start_time: float = None,
    overall_started_at: str = None,
) -> tuple[str, list[object]]:
    created_transactions = []

    llm_calls = []
    if intent_step_info:
        llm_calls.append(intent_step_info)

    status = "success"

    if parse_result.get("intent") == INTENT_TRANSACTION_BATCH:
        actions = parse_result.get("actions") or []
        try:
            with transaction.atomic():
                for action in actions:
                    created_transactions.append(
                        create_transaction(
                            user=user,
                            category_id=str(action["category_id"]),
                            amount=Decimal(str(action["amount"])),
                            description=action.get("description"),
                            transaction_date=datetime.strptime(
                                action["transaction_date"], "%Y-%m-%d"
                            ).date(),
                        )
                    )
        except (KeyError, ValueError, TransactionServiceError) as exc:
            raise TransactionServiceError(str(exc)) from exc

    response_message = ""
    if parse_result.get("intent") == INTENT_FINANCIAL_QUESTION:
        subject_scope = parse_result.get("subject_scope")
        if subject_scope == SUBJECT_SCOPE_OTHER_PERSON:
            response_message = FINANCIAL_OTHER_PERSON_MESSAGE
            status = "failed"
        elif subject_scope == SUBJECT_SCOPE_AMBIGUOUS:
            response_message = FINANCIAL_AMBIGUOUS_MESSAGE
            status = "failed"
        else:
            sql = parse_result.get("sql")
            if not sql:
                response_message = "I couldn't compile a query for your question."
                status = "failed"
            else:
                try:
                    sanitized_sql = validate_and_sanitize_sql(
                        sql, str(user.id).replace("-", "")
                    )
                    with connection.cursor() as cursor:
                        cursor.execute(sanitized_sql)
                        columns = (
                            [col[0] for col in cursor.description]
                            if cursor.description
                            else []
                        )
                        rows = list(cursor.fetchall())

                    formatted_rows = []
                    for row in rows:
                        formatted_row = []
                        for item in row:
                            if isinstance(item, Decimal):
                                formatted_row.append(float(item))
                            elif isinstance(item, (datetime, date)):
                                formatted_row.append(item.isoformat())
                            else:
                                formatted_row.append(item)
                        formatted_rows.append(formatted_row)

                    parse_result["query_result"] = {
                        "columns": columns,
                        "rows": formatted_rows,
                        "sql": sanitized_sql,
                    }

                    response_msg, eval_step_info = evaluate_financial_data_with_llm(
                        user_question=user_message,
                        query_data=parse_result["query_result"],
                    )
                    response_message = response_msg
                    llm_calls.append(eval_step_info)
                except Exception as exc:
                    response_message = "An error occurred while compiling your request. Please try again."
                    parse_result["query_error"] = str(exc)
                    status = "failed"
    else:
        response_message = _build_commit_message(
            parse_result, len(created_transactions)
        )
        if (
            not created_transactions
            and parse_result.get("intent") == INTENT_TRANSACTION_BATCH
        ):
            status = "partial" if parse_result.get("rejected_actions") else "failed"

    import time

    overall_finished_at = datetime.now()
    if overall_start_time:
        overall_latency = int((time.time() - overall_start_time) * 1000)
    else:
        overall_latency = 0
        overall_started_at = overall_finished_at.isoformat()

    AIChatMessage.objects.create(
        user=user,
        sender="user",
        content=user_message,
    )
    AIChatMessage.objects.create(
        user=user,
        sender="assistant",
        content=response_message,
        metadata={
            "started_at": overall_started_at,
            "finished_at": overall_finished_at.isoformat(),
            "latency_ms": overall_latency,
            "status": status,
            "raw_llm_output": raw_llm_output,
            "model": model_name,
            "parse_result": parse_result,
            "llm_calls": llm_calls,
        },
    )

    return response_message, created_transactions


# def parse_message_for_commit(
#     user: User, message: str
# ) -> tuple[dict[str, Any], str, str]:
#     system_instruction = _build_system_instruction(user=user)
#     raw_llm_output = _call_gemini(
#         message=message, system_instruction=system_instruction
#     )
#     result = _validate_llm_output(raw_text=raw_llm_output, user=user)

#     if result.get("intent") == INTENT_UNKNOWN:
#         reason = _infer_unknown_reason(message)
#         if reason:
#             result["reason"] = reason

#     model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
#     return result, raw_llm_output, model_name


def evaluate_financial_data_with_llm(
    user_question: str, query_data: dict
) -> tuple[str, dict]:
    import time

    start_t = time.time()
    started_at = datetime.now()

    now_iso = started_at.isoformat()
    system_instruction = f"""Bạn là một trợ lý ảo tư vấn tài chính cá nhân thông minh và thân thiện.
Nhiệm vụ của bạn là đọc dữ liệu tài chính (được truy xuất từ cơ sở dữ liệu) và trả lời câu hỏi của người dùng một cách tự nhiên, dễ hiểu.

THÔNG TIN HỆ THỐNG:
- Thời gian hiện tại: {now_iso}

ĐẦU VÀO CỦA BẠN SẼ BAO GỒM:
1. Câu hỏi gốc của người dùng (User Question).
2. Dữ liệu tài chính (Query Result) dưới dạng JSON, bao gồm 'columns' (tên các cột), 'rows' (dữ liệu của từng dòng), và 'sql'.

YÊU CẦU TRẢ LỜI:
- Phân tích và tổng hợp số liệu từ 'Query Result' để trả lời trực tiếp, chính xác cho 'User Question'.
- NẾU câu hỏi của người dùng có đề cập đến khoảng thời gian (ví dụ: "tháng này", "3 tháng trước", "trong năm nay"), BẠN PHẢI TÍNH TOÁN và XÁC ĐỊNH chính xác khoảng thời gian đó dựa vào 'Thời gian hiện tại'.

- QUY TẮC FORMAT THỜI GIAN:
  + Nếu khoảng thời gian bao phủ theo THÁNG hoặc NĂM (ví dụ: "this month", "past 6 months", "this year"), CHỈ hiển thị "Month Year" hoặc "Month Year to Month Year".
    Ví dụ:
      - "this month" -> "May 2026"
      - "past 6 months" -> "December 2025 to May 2026"
    KHÔNG hiển thị ngày cụ thể.

  + Chỉ hiển thị ngày cụ thể nếu khoảng thời gian dựa trên DAY-level:
      - "last 7 days"
      - "past 30 days"
      - "from May 3 to May 18"

  + Ưu tiên:
      "Here is your spending summary for May 2026."
    thay vì:
      "Here is your spending summary for this month (from May 1, 2026, to May 21, 2026)."
- CHÈN khoảng thời gian đã tính toán vào câu mở đầu nếu phù hợp.
- KHÔNG hiển thị cấu trúc JSON, mảng (array) hay mã SQL cho người dùng. Hãy trình bày đẹp mắt dưới dạng danh sách hoặc đoạn văn tự nhiên. 
- Nếu 'Query Result' rỗng (không có dữ liệu/rows rỗng), hãy thông báo khéo léo rằng không có giao dịch hoặc số liệu nào khớp với yêu cầu tìm kiếm của người dùng trong khoảng thời gian đó.
- Trả lời bằng ngôn ngữ Tiếng Anh.
- Giữ văn phong lịch sự, ngắn gọn. Nếu phù hợp, có thể đưa ra một nhận xét hoặc lời khuyên tài chính nho nhỏ dựa trên dữ liệu.
"""

    user_prompt = f"Câu hỏi của người dùng: {user_question}\n\nDữ liệu tài chính (JSON):\n{json.dumps(query_data, ensure_ascii=False)}"

    raw_llm_output = _call_gemini(
        message=user_prompt,
        system_instruction=system_instruction,
        response_mime_type="text/plain",
    )

    finished_at = datetime.now()
    latency_ms = int((time.time() - start_t) * 1000)
    step_info = {
        "step": "evaluate_financial_data",
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "latency_ms": latency_ms,
    }

    return raw_llm_output.strip(" \n\r\"'"), step_info


# - NẾU câu hỏi của người dùng có đề cập đến khoảng thời gian (ví dụ: "tháng này", "3 tháng trước", "trong năm nay"), BẠN PHẢI TÍNH TOÁN và XÁC ĐỊNH chính xác khoảng thời gian đó (ngày tháng bắt đầu/kết thúc) dựa vào 'Thời gian hiện tại' và CHÈN KHOẢNG THỜI GIAN ĐÓ vào câu mở đầu của câu trả lời.
#   (Ví dụ: "Dưới đây là 5 khoản chi tiêu lớn nhất của bạn trong 3 tháng qua (từ tháng 10/2025 đến tháng 01/2026):" hoặc "Here are your top 5 expenses over the past 3 months (from October 15, 2025, to January 15, 2026):").
