from __future__ import annotations

import random
import secrets
import string


def random_sequence() -> int:
    """
    Generate the integer request identifier supplied to initIotcReq().

    The Android/native application uses rand(). A positive 31-bit integer
    is suitable for reproducing that role.
    """

    return random.randint(1, 0x7FFFFFFF)


def create_seed(length: int = 32) -> bytes:
    """
    Equivalent character set to Functions.getCharAndNumr():

        A-Z
        a-z
        0-9
    """

    if length <= 0:
        raise ValueError("Seed length must be greater than zero.")

    alphabet = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    ).encode("ascii")