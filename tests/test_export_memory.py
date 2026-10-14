"""Export planning releases full responses after extracting selected records."""
import gc
import weakref
import threading

from pyincucyte import engine


def test_completed_scan_responses_are_released_during_planning(tmp_path, monkeypatch):
    class Payload:
        pass

    payloads = []
    released = []
    peak_live = []
    lock = threading.Lock()

    def api_post(*args):
        payload = Payload()
        with lock:
            payloads.append(weakref.ref(payload))
            peak_live.append(sum(ref() is not None for ref in payloads))
        return {"Data": {"ImageInfos": [{
            "Swell": {"RowZeroBased": 0, "ColumnZeroBased": 0},
            "SwellSite": {"ValueZeroBased": 0}, "ImageType": 1,
            "UnusedScanMetadata": payload,
        }]}}

    def progress(*args):
        gc.collect()
        released.append(sum(ref() is None for ref in payloads))

    monkeypatch.setattr(engine, "api_post", api_post)
    times = [f"2026-03-01T09:{minute:02d}:00" for minute in range(32)]
    items = engine.collect_time_stacks(
        "host", "token", 38, times, tmp_path, max_workers=2,
        progress_callback=progress)
    assert len(items) == 1
    assert items[0]["scan_times"] == times
    assert released[-1] >= len(times) - 2
    assert max(peak_live) <= 4  # At most two responses per worker.


def test_stop_during_request_does_not_plan_completed_response(tmp_path, monkeypatch):
    stop = threading.Event()
    def api_post(*args):
        stop.set()
        return {"Data": {"ImageInfos": [{"ImageType": 1}]}}
    monkeypatch.setattr(engine, "api_post", api_post)
    items = engine.collect_time_stacks(
        "host", "token", 38,
        [f"2026-03-01T09:{minute:02d}:00" for minute in range(20)],
        tmp_path, max_workers=2, stop_event=stop)
    assert items == []

