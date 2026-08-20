from __future__ import annotations

import base64
import json
import secrets
import uuid
from typing import Any

from ..crypto.curve25519 import Curve25519Session
from .models import (
    DeviceMqttInfo,
    TurnRelayInfo,
    WakeupRequest,
    WakeupResult,
)
from .payload import build_message_payload
from .topics import (
    build_wakeup_publish_topic,
    build_wakeup_response_topic,
)


WAKEUP_CALL_REQUEST = 1
WAKEUP_CALL_RESPONSE = 2
WAKEUP_SUCCESS_CODE = 1000


def create_message_id() -> int:
    """
    Produce a positive Java-compatible signed integer.
    """

    return (
        secrets.randbelow(
            0x7FFFFFFF - 10
        )
        + 10
    )


def create_thread_id() -> int:
    """
    The app uses a positive identifier for the MQTT
    response topic and wake-up context.
    """

    return (
        secrets.randbelow(
            0x7FFFFFFF - 10
        )
        + 10
    )


def build_wakeup_context(
    *,
    client_uuid: str,
    client_public_key: bytes,
    thread_id: int,
    relay: TurnRelayInfo | None = None,
) -> dict[str, Any]:
    """
    Reproduce MqttHelper.createCallInWakeUp().

    Without relay information:

        {
            "id": thread_id,
            "auth": {
                "uuid": "...",
                "pubKC": "..."
            }
        }

    With relay information:

        {
            "turn": {
                "host": "...",
                "port": ...,
                "hdl": ...
            },
            "auth": {
                "uuid": "...",
                "pubKC": "..."
            }
        }
    """

    if not client_uuid:
        raise ValueError(
            "Client UUID cannot be empty."
        )

    if len(client_public_key) != 32:
        raise ValueError(
            "Client public key must contain "
            "exactly 32 bytes."
        )

    if thread_id <= 0:
        raise ValueError(
            "Thread ID must be positive."
        )

    context: dict[str, Any] = {}

    if relay is None:
        context["id"] = thread_id
    else:
        context["turn"] = {
            "host": relay.host,
            "port": relay.port,
            "hdl": relay.handle,
        }

    context["auth"] = {
        "uuid": client_uuid,
        "pubKC": base64.b64encode(
            client_public_key
        ).decode("ascii"),
    }

    return context


def build_wakeup_request(
    *,
    device: DeviceMqttInfo,
    curve_session: Curve25519Session | None = None,
    relay: TurnRelayInfo | None = None,
    message_id: int | None = None,
    thread_id: int | None = None,
    client_uuid: str | None = None,
    timestamp_seconds: int | None = None,
) -> tuple[WakeupRequest, Curve25519Session]:
    """
    Build the pver >= 5 wake-up message recovered from
    MqttHelper.AppCallDeviceWakeUp().
    """

    session = (
        curve_session
        if curve_session is not None
        else Curve25519Session()
    )

    key_pair = session.generate()

    resolved_message_id = (
        create_message_id()
        if message_id is None
        else message_id
    )

    resolved_thread_id = (
        create_thread_id()
        if thread_id is None
        else thread_id
    )

    resolved_uuid = (
        str(uuid.uuid4())
        if client_uuid is None
        else client_uuid
    )

    context = build_wakeup_context(
        client_uuid=resolved_uuid,
        client_public_key=key_pair.public_key,
        thread_id=resolved_thread_id,
        relay=relay,
    )

    document: dict[str, Any] = {
        "call": WAKEUP_CALL_REQUEST,
        "mid": resolved_message_id,
        "ctx": context,
    }

    json_text = json.dumps(
        document,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    source = device.device_identity
    destination = device.account_identity

    encrypted_payload = build_message_payload(
        source=source,
        destination=destination,
        rand_key=device.rand_key,
        json_text=json_text,
        flag=0,
        properties=b"",
        timestamp_seconds=timestamp_seconds,
    )

    publish_topic = (
        build_wakeup_publish_topic(
            device_id=device.device_id,
            account_uid=device.account_uid,
        )
    )

    response_topic = (
        build_wakeup_response_topic(
            resolved_thread_id
        )
    )

    request = WakeupRequest(
        message_id=resolved_message_id,
        thread_id=resolved_thread_id,
        client_uuid=resolved_uuid,
        client_public_key=key_pair.public_key,
        response_topic=response_topic,
        json_document=document,
        json_text=json_text,
        encrypted_payload=encrypted_payload,
        publish_topic=publish_topic,
    )

    return request, session


def parse_wakeup_response(
    document: dict[str, Any],
) -> WakeupResult:
    """
    Parse the decrypted MqttCallJsonParse wake-up response.

    Expected structure:

        {
            "call": 2,
            "mid": ...,
            "ctx": {
                "id": ...,
                "result": {
                    "code": 1000,
                    "desc": "..."
                }
            }
        }
    """

    call = _read_integer(
        document,
        "call",
    )

    if call is None:
        raise ValueError(
            "Wake-up response has no integer 'call' field."
        )

    message_id = _read_integer(
        document,
        "mid",
    )

    context = document.get("ctx")

    if not isinstance(context, dict):
        context = {}

    thread_id = _read_integer(
        context,
        "id",
    )

    result_object = context.get("result")

    if not isinstance(result_object, dict):
        result_object = {}

    result_code = _read_integer(
        result_object,
        "code",
    )

    result_description = (
        _read_string(
            result_object,
            "desc",
        )
    )

    return WakeupResult(
        call=call,
        message_id=message_id,
        thread_id=thread_id,
        result_code=result_code,
        result_description=result_description,
        raw_document=document,
    )


def parse_wakeup_response_text(
    plaintext: str,
) -> WakeupResult:
    try:
        document = json.loads(
            plaintext
        )
    except json.JSONDecodeError as error:
        raise ValueError(
            "Wake-up response is not valid JSON."
        ) from error

    if not isinstance(document, dict):
        raise ValueError(
            "Wake-up response root must be "
            "a JSON object."
        )

    return parse_wakeup_response(
        document
    )


def validate_wakeup_result(
    result: WakeupResult,
    request: WakeupRequest,
) -> None:
    if result.call != WAKEUP_CALL_RESPONSE:
        raise ValueError(
            "Unexpected wake-up call value: "
            f"{result.call}. Expected "
            f"{WAKEUP_CALL_RESPONSE}."
        )

    if (
        result.message_id is not None
        and result.message_id
        != request.message_id
    ):
        raise ValueError(
            "Wake-up response message ID does not "
            "match the request."
        )

    if (
        result.thread_id is not None
        and result.thread_id
        != request.thread_id
    ):
        raise ValueError(
            "Wake-up response thread ID does not "
            "match the request."
        )

    if result.result_code != WAKEUP_SUCCESS_CODE:
        description = (
            result.result_description
            or "no description"
        )

        raise PermissionError(
            "Camera rejected MQTT wake-up: "
            f"code={result.result_code}, "
            f"description={description}"
        )


def _read_integer(
    document: dict[str, Any],
    name: str,
) -> int | None:
    value = document.get(name)

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if value.is_integer():
            return int(value)

    return None


def _read_string(
    document: dict[str, Any],
    name: str,
) -> str | None:
    value = document.get(name)

    if isinstance(value, str):
        return value

    return None