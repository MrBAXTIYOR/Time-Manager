"""UUIDv7 generator (RFC 9562).

Layout (128 bits):  48-bit unix time in ms | 4-bit version (7) | 12-bit counter
                    | 2-bit variant (10) | 62 random bits

Python 3.12 has no uuid.uuid7 (added in 3.14), so we implement it. Because the
timestamp is the most significant part, UUIDv7 values sort by creation time,
which keeps InnoDB's clustered primary-key index append-mostly (fast inserts,
unlike random UUIDv4). The 12-bit counter keeps values strictly increasing
inside one process even when several are created within the same millisecond.
"""

import os
import threading
import time
import uuid

_lock = threading.Lock()
_last_ms = 0
_counter = 0


def _rand_counter() -> int:
    # Start below 0x800 to leave headroom so the counter rarely overflows.
    return int.from_bytes(os.urandom(2), "big") & 0x7FF


def uuid7() -> uuid.UUID:
    global _last_ms, _counter
    with _lock:
        now_ms = time.time_ns() // 1_000_000
        if now_ms > _last_ms:
            _last_ms = now_ms
            _counter = _rand_counter()
        else:  # same ms (or clock went backwards): keep ordering monotonic
            _counter += 1
            if _counter > 0xFFF:  # 12-bit overflow -> borrow from the timestamp
                _last_ms += 1
                _counter = _rand_counter()
        ms, counter = _last_ms, _counter

    rand_b = int.from_bytes(os.urandom(8), "big") & ((1 << 62) - 1)
    value = (ms << 80) | (0x7 << 76) | (counter << 64) | (0b10 << 62) | rand_b
    return uuid.UUID(int=value)


def uuid7_timestamp_ms(value: uuid.UUID) -> int:
    """Extract the embedded creation time (ms since epoch)."""
    return value.int >> 80
