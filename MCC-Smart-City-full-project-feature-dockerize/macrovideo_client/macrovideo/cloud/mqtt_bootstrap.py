from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import httpx


DEFAULT_MQTT_LOGIN_SERVER = "gmdev.av380.net:8443"
DEFAULT_MQTT_PROTOCOL_VERSION = 3
MQTT_SIGNING_SECRET = "oplatformV1"

MQTT_LOGIN_SUCCESS = 5600
MQTT_LOGIN_UNAUTHORIZED = 5607


@dataclass(frozen=True)
class MqttClientMetadata:
    app_version: str
    system_version: str
    brand: str

    def __post_init__(self) -> None:
        if not self.app_version:
            raise ValueError(
                "MQTT client app version cannot be empty."
            )

        if not self.system_version:
            raise ValueError(
                "MQTT client system version cannot be empty."
            )

        if not self.brand:
            raise ValueError(
                "MQTT client brand cannot be empty."
            )

    def to_document(self) -> dict[str, str]:
        return {
            "AV": self.app_version,
            "SV": self.system_version,
            "BR": self.brand,
        }


@dataclass(frozen=True)
class MqttBootstrapDeviceInfo:
    device_id: int
    protocol_version: int = 0
    rand_key: str = ""
    master_id: int = 0
    raw_document: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class MqttBootstrapRequest:
    account_uid: int
    access_token: str
    protocol_version: int
    metadata: MqttClientMetadata
    server: str
    timestamp_ms: int
    compact_json: str
    signature: str
    url: str
    document: dict[str, Any]


@dataclass(frozen=True)
class MqttBootstrapResult:
    code: int
    broker_url: str
    client_id: str
    username: str
    password: str
    expires_at: int
    devices: dict[int, MqttBootstrapDeviceInfo]
    raw_document: dict[str, Any]

    @property
    def succeeded(self) -> bool:
        return (
            self.code == MQTT_LOGIN_SUCCESS
            and bool(self.broker_url)
            and bool(self.client_id)
            and bool(self.username)
            and bool(self.password)
        )

    @property
    def paho_transport_url(self) -> str:
        if self.broker_url.startswith(
            "mqtts://"
        ):
            return self.broker_url.replace(
                "mqtts://",
                "ssl://",
                1,
            )

        if self.broker_url.startswith(
            "mqtt://"
        ):
            return self.broker_url.replace(
                "mqtt://",
                "tcp://",
                1,
            )

        return self.broker_url

    def find_device(
        self,
        device_id: int,
    ) -> MqttBootstrapDeviceInfo | None:
        return self.devices.get(device_id)


class MqttBootstrapError(RuntimeError):
    pass


class MqttBootstrapUnauthorizedError(
    MqttBootstrapError
):
    pass


def calculate_md5_hex(value: str) -> str:
    return hashlib.md5(
        value.encode("utf-8")
    ).hexdigest()


def serialize_mqtt_login_document(
    document: dict[str, Any],
) -> str:
    return json.dumps(
        document,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def create_mqtt_login_signature(
    compact_json: str,
    timestamp_ms: int,
) -> str:
    if not compact_json:
        raise ValueError(
            "MQTT login JSON cannot be empty."
        )

    if timestamp_ms <= 0:
        raise ValueError(
            "MQTT login timestamp must be positive."
        )

    inner_hash = calculate_md5_hex(
        compact_json + MQTT_SIGNING_SECRET
    )

    return calculate_md5_hex(
        inner_hash + str(timestamp_ms)
    )


def normalize_mqtt_server(
    server: str,
) -> str:
    cleaned = server.strip()

    if not cleaned:
        raise ValueError(
            "MQTT login server cannot be empty."
        )

    for prefix in (
        "https://",
        "http://",
    ):
        if cleaned.startswith(prefix):
            cleaned = cleaned.removeprefix(
                prefix
            )

    return cleaned.rstrip("/")


def build_mqtt_bootstrap_request(
    *,
    account_uid: int,
    access_token: str,
    metadata: MqttClientMetadata,
    server: str = DEFAULT_MQTT_LOGIN_SERVER,
    protocol_version: int = (
        DEFAULT_MQTT_PROTOCOL_VERSION
    ),
    timestamp_ms: int | None = None,
) -> MqttBootstrapRequest:
    if account_uid <= 0:
        raise ValueError(
            "Account UID must be positive."
        )

    if not access_token:
        raise ValueError(
            "Account access token cannot be empty."
        )

    if protocol_version <= 0:
        raise ValueError(
            "MQTT protocol version must be positive."
        )

    resolved_server = normalize_mqtt_server(
        server
    )

    resolved_timestamp = (
        int(time.time() * 1000)
        if timestamp_ms is None
        else timestamp_ms
    )

    document: dict[str, Any] = {
        "UID": account_uid,
        "atoken": access_token,
        "pver": protocol_version,
        "client": metadata.to_document(),
    }

    compact_json = (
        serialize_mqtt_login_document(
            document
        )
    )

    signature = create_mqtt_login_signature(
        compact_json,
        resolved_timestamp,
    )

    query = urlencode(
        {
            "signature": signature,
            "timestamp": resolved_timestamp,
        }
    )

    url = (
        f"https://{resolved_server}"
        f"/v1/app/login?{query}"
    )

    return MqttBootstrapRequest(
        account_uid=account_uid,
        access_token=access_token,
        protocol_version=protocol_version,
        metadata=metadata,
        server=resolved_server,
        timestamp_ms=resolved_timestamp,
        compact_json=compact_json,
        signature=signature,
        url=url,
        document=document,
    )


def request_mqtt_credentials(
    *,
    account_uid: int,
    access_token: str,
    metadata: MqttClientMetadata,
    server: str = DEFAULT_MQTT_LOGIN_SERVER,
    protocol_version: int = (
        DEFAULT_MQTT_PROTOCOL_VERSION
    ),
    timestamp_ms: int | None = None,
    timeout: float = 45.0,
    verify_tls: bool = True,
    attempts: int = 3,
    retry_delay: float = 2.0,
) -> MqttBootstrapResult:
    if timeout <= 0:
        raise ValueError(
            "MQTT bootstrap timeout must be positive."
        )

    if attempts <= 0:
        raise ValueError(
            "MQTT bootstrap attempts must be positive."
        )

    if retry_delay < 0:
        raise ValueError(
            "MQTT bootstrap retry delay cannot "
            "be negative."
        )

    last_error: Exception | None = None

    for attempt in range(
        1,
        attempts + 1,
    ):
        resolved_timestamp = (
            timestamp_ms
            if timestamp_ms is not None
            else int(time.time() * 1000)
        )

        request = build_mqtt_bootstrap_request(
            account_uid=account_uid,
            access_token=access_token,
            metadata=metadata,
            server=server,
            protocol_version=protocol_version,
            timestamp_ms=resolved_timestamp,
        )

        print(
            "[MQTT bootstrap] "
            f"Attempt {attempt}/{attempts}: "
            f"https://{request.server}"
            "/v1/app/login"
        )

        try:
            client_timeout = httpx.Timeout(
                timeout,
                connect=timeout,
                read=timeout,
                write=timeout,
                pool=timeout,
            )

            with httpx.Client(
                timeout=client_timeout,
                verify=verify_tls,
                follow_redirects=True,
                trust_env=False,
                headers={
                    "Accept": "application/json",
                    "Content-Type": (
                        "application/json; "
                        "charset=utf-8"
                    ),
                    "Connection": "close",
                },
            ) as client:
                response = client.post(
                    request.url,
                    content=(
                        request.compact_json.encode(
                            "utf-8"
                        )
                    ),
                )

            if response.status_code >= 400:
                preview = response.text[:500]

                raise ConnectionError(
                    "MQTT credential server "
                    "returned HTTP "
                    f"{response.status_code}: "
                    f"{preview}"
                )

            try:
                document = response.json()
            except json.JSONDecodeError as error:
                raise ValueError(
                    "MQTT credential response was "
                    "not valid JSON: "
                    f"{response.text[:500]}"
                ) from error

            if not isinstance(
                document,
                dict,
            ):
                raise ValueError(
                    "MQTT credential response root "
                    "is not a JSON object."
                )

            return (
                parse_mqtt_bootstrap_response(
                    document
                )
            )

        except httpx.TimeoutException as error:
            last_error = TimeoutError(
                "MQTT credential request timed out "
                f"on attempt {attempt}/{attempts}: "
                f"{type(error).__name__}"
            )

        except httpx.RequestError as error:
            last_error = ConnectionError(
                "Could not contact MQTT credential "
                f"server on attempt "
                f"{attempt}/{attempts}: {error}"
            )

        except (
            ConnectionError,
            ValueError,
        ) as error:
            last_error = error

        if attempt < attempts:
            print(
                "[MQTT bootstrap] Request failed; "
                f"retrying in "
                f"{retry_delay:.1f} seconds."
            )

            time.sleep(
                retry_delay
            )

    if last_error is not None:
        raise last_error

    raise RuntimeError(
        "MQTT credential request failed "
        "without recording an error."
    )


def parse_mqtt_bootstrap_response(
    document: dict[str, Any],
) -> MqttBootstrapResult:
    code = _read_integer(
        document,
        "code",
        default=-1,
    )

    if code == MQTT_LOGIN_UNAUTHORIZED:
        raise MqttBootstrapUnauthorizedError(
            "MQTT credential server rejected "
            "the account token with code 5607."
        )

    if code != MQTT_LOGIN_SUCCESS:
        raise MqttBootstrapError(
            "MQTT credential server returned "
            f"unexpected code {code}."
        )

    data = document.get("data")

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "Successful MQTT response contains "
            "no `data` object."
        )

    broker_url = _read_string(
        data,
        "url",
    )

    client_id = _read_first_string(
        data,
        (
            "cid",
            "client_id",
            "clientId",
        ),
    )

    username = _read_first_string(
        data,
        (
            "user",
            "username",
        ),
    )

    password = _read_first_string(
        data,
        (
            "pass",
            "password",
        ),
    )

    expires_at = _read_integer(
        data,
        "expired",
        default=0,
    )

    missing = [
        name
        for name, value in (
            ("data.url", broker_url),
            ("data.cid", client_id),
            ("data.user", username),
            ("data.pass", password),
        )
        if not value
    ]

    if missing:
        raise ValueError(
            "MQTT credential response is "
            "missing: "
            + ", ".join(missing)
        )

    devices = _extract_device_map(
        data
    )

    return MqttBootstrapResult(
        code=code,
        broker_url=broker_url,
        client_id=client_id,
        username=username,
        password=password,
        expires_at=expires_at,
        devices=devices,
        raw_document=document,
    )


def mask_mqtt_bootstrap_document(
    document: dict[str, Any],
) -> dict[str, Any]:
    copied = json.loads(
        json.dumps(document)
    )

    sensitive_names = {
        "pass",
        "password",
        "user",
        "username",
        "atoken",
        "access_token",
        "accesstoken",
        "rk",
        "randkey",
        "rand_key",
    }

    def walk(value: Any) -> None:
        if isinstance(
            value,
            dict,
        ):
            for key, child in list(
                value.items()
            ):
                if (
                    key.lower()
                    in sensitive_names
                    and isinstance(
                        child,
                        str,
                    )
                ):
                    value[key] = _mask(
                        child
                    )
                else:
                    walk(child)

        elif isinstance(
            value,
            list,
        ):
            for child in value:
                walk(child)

    walk(copied)
    return copied


def _extract_device_map(
    data: dict[str, Any],
) -> dict[int, MqttBootstrapDeviceInfo]:
    candidates: list[Any] = []

    for name in (
        "devices",
        "device_list",
        "deviceList",
        "devs",
        "deviceMqInfoMap",
        "mq_devices",
        "mqDevices",
    ):
        if name in data:
            candidates.append(
                data[name]
            )

    found: dict[
        int,
        MqttBootstrapDeviceInfo,
    ] = {}

    def add(
        item: dict[str, Any],
        fallback_id: int = 0,
    ) -> None:
        device_id = _read_first_integer(
            item,
            (
                "did",
                "device_id",
                "deviceId",
                "id",
            ),
            fallback_id,
        )

        if device_id <= 0:
            return

        found[device_id] = (
            MqttBootstrapDeviceInfo(
                device_id=device_id,
                protocol_version=(
                    _read_first_integer(
                        item,
                        (
                            "pver",
                            "ver",
                            "protocol_version",
                        ),
                        0,
                    )
                ),
                rand_key=(
                    _read_first_string(
                        item,
                        (
                            "rk",
                            "randKey",
                            "rand_key",
                        ),
                    )
                ),
                master_id=(
                    _read_first_integer(
                        item,
                        (
                            "masterId",
                            "master_id",
                            "uid",
                            "owner_id",
                        ),
                        0,
                    )
                ),
                raw_document=item,
            )
        )

    for candidate in candidates:
        if isinstance(
            candidate,
            list,
        ):
            for item in candidate:
                if isinstance(
                    item,
                    dict,
                ):
                    add(item)

        elif isinstance(
            candidate,
            dict,
        ):
            for key, item in (
                candidate.items()
            ):
                fallback = (
                    int(key)
                    if str(key).isdigit()
                    else 0
                )

                if isinstance(
                    item,
                    dict,
                ):
                    add(
                        item,
                        fallback,
                    )

    return found


def _mask(
    value: str,
) -> str:
    if len(value) <= 8:
        return "*" * len(value)

    return (
        value[:4]
        + "*" * (len(value) - 8)
        + value[-4:]
    )


def _read_integer(
    document: dict[str, Any],
    name: str,
    *,
    default: int,
) -> int:
    return _coerce_integer(
        document.get(name),
        default,
    )


def _read_first_integer(
    document: dict[str, Any],
    names: tuple[str, ...],
    default: int,
) -> int:
    for name in names:
        value = _coerce_integer(
            document.get(name),
            default,
        )

        if value != default:
            return value

    return default


def _coerce_integer(
    value: Any,
    default: int,
) -> int:
    if isinstance(
        value,
        bool,
    ):
        return default

    if isinstance(
        value,
        int,
    ):
        return value

    if (
        isinstance(
            value,
            float,
        )
        and value.is_integer()
    ):
        return int(value)

    if isinstance(
        value,
        str,
    ):
        try:
            return int(
                value.strip()
            )
        except ValueError:
            return default

    return default


def _read_string(
    document: dict[str, Any],
    name: str,
) -> str:
    value = document.get(name)

    if isinstance(
        value,
        str,
    ):
        return value.strip()

    if value is None:
        return ""

    return str(value).strip()


def _read_first_string(
    document: dict[str, Any],
    names: tuple[str, ...],
) -> str:
    for name in names:
        value = _read_string(
            document,
            name,
        )

        if value:
            return value

    return ""