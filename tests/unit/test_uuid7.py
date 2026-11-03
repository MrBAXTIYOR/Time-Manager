import time
import uuid

from app.core.uuid7 import uuid7, uuid7_timestamp_ms


def test_version_and_variant_bits():
    u = uuid7()
    assert u.version == 7
    assert u.variant == uuid.RFC_4122


def test_embeds_current_time():
    before = int(time.time() * 1000)
    u = uuid7()
    after = int(time.time() * 1000)
    assert before <= uuid7_timestamp_ms(u) <= after + 1


def test_strictly_increasing_even_within_one_millisecond():
    values = [uuid7() for _ in range(20_000)]  # far more than 1 per ms
    assert values == sorted(values)
    assert len(set(values)) == len(values)


def test_byte_order_matches_time_order():
    """BINARY(16) is compared byte-wise: bytes must sort like creation time."""
    first = uuid7()
    time.sleep(0.003)
    second = uuid7()
    assert first.bytes < second.bytes


def test_counter_overflow_borrows_from_timestamp_and_stays_monotonic(monkeypatch):
    """Force >4096 ids inside one 'frozen' millisecond: the 12-bit counter must
    overflow into the timestamp instead of wrapping (which would break ordering)."""
    from app.core import uuid7 as mod

    frozen_ns = 1_800_000_000_000 * 1_000_000
    monkeypatch.setattr(mod.time, "time_ns", lambda: frozen_ns)
    monkeypatch.setattr(mod, "_last_ms", 0)
    values = [mod.uuid7() for _ in range(10_000)]
    assert values == sorted(values) and len(set(values)) == 10_000
    assert max(mod.uuid7_timestamp_ms(v) for v in values) > 1_800_000_000_000  # borrowed
