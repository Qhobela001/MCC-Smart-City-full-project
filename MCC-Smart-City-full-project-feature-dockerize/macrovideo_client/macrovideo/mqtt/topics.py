from __future__ import annotations


def build_device_identity(
    device_id: int,
) -> str:
    if device_id <= 0:
        raise ValueError(
            "Device ID must be greater than zero."
        )

    return f"CID{device_id}"


def build_user_identity(
    account_uid: int,
) -> str:
    if account_uid <= 0:
        raise ValueError(
            "Account UID must be greater than zero."
        )

    return f"UID{account_uid}"


def build_wakeup_publish_topic(
    *,
    device_id: int,
    account_uid: int,
) -> str:
    """
    Recovered MqttHelper publish topic:

        CID/CID<device_id>/UID/UID<account_uid>/call
    """

    device_identity = build_device_identity(
        device_id
    )

    user_identity = build_user_identity(
        account_uid
    )

    return (
        f"CID/{device_identity}/"
        f"UID/{user_identity}/call"
    )


def build_wakeup_response_topic(
    thread_id: int,
) -> str:
    """
    Recovered MQTT v5 response topic:

        WakeUp/<thread_id>
    """

    if thread_id <= 0:
        raise ValueError(
            "Wake-up thread ID must be positive."
        )

    return f"WakeUp/{thread_id}"


def build_device_subscription_topic(
    device_id: int,
) -> str:
    """
    Broad device topic used when listening for messages
    addressed to a camera.
    """

    device_identity = build_device_identity(
        device_id
    )

    return f"CID/{device_identity}/#"


def build_user_subscription_topic(
    account_uid: int,
) -> str:
    """
    Broad account topic used when listening for messages
    addressed to the signed-in user.
    """

    user_identity = build_user_identity(
        account_uid
    )

    return f"UID/{user_identity}/#"