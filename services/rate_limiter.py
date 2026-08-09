"""
Guards live ZentraCloud calls against their documented limits:
  - 60 total calls/minute per account
  - 1 call/minute per individual device

Source: ZentraCloud US Server API docs — "Users are limited to a total
of 60 calls per minute, and each device is limited to 1 call per
minute. One user can make 60 calls to 60 different devices in a 60
second period."

This is intentionally lightweight (in-process, in-memory) — fine for a
single Flask process. If you ever run multiple worker processes behind
gunicorn, this state won't be shared across them and you'd want to
move it to something shared (e.g. Redis) instead.
"""

import time
import threading

MAX_CALLS_PER_MINUTE = 55  # small safety margin under ZentraCloud's documented 60/min
MIN_SECONDS_PER_DEVICE = 61  # documented limit is 1 call/minute per device

_lock = threading.Lock()
_call_timestamps = []       # timestamps of recent calls, any device
_last_call_per_device = {}  # serial_number -> last call timestamp


def wait_if_needed(serial_number):
    """
    Blocks (sleeps) just long enough to stay under both limits before
    a live call to this device. Call this immediately before each
    live requests.get(...) to ZentraCloud.
    """
    with _lock:
        now = time.time()

        # Drop timestamps older than 60s — they no longer count toward the limit.
        global _call_timestamps
        _call_timestamps = [t for t in _call_timestamps if now - t < 60]

        wait_for_total = 0
        if len(_call_timestamps) >= MAX_CALLS_PER_MINUTE:
            oldest = _call_timestamps[0]
            wait_for_total = max(0, 60 - (now - oldest))

        wait_for_device = 0
        last_for_this_device = _last_call_per_device.get(serial_number)
        if last_for_this_device is not None:
            elapsed = now - last_for_this_device
            if elapsed < MIN_SECONDS_PER_DEVICE:
                wait_for_device = MIN_SECONDS_PER_DEVICE - elapsed

        wait_time = max(wait_for_total, wait_for_device)

    if wait_time > 0:
        time.sleep(wait_time)

    with _lock:
        now = time.time()
        _call_timestamps.append(now)
        _last_call_per_device[serial_number] = now
