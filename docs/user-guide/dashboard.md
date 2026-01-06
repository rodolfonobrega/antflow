# Dashboard and Monitoring

AntFlow provides comprehensive tools for monitoring pipeline execution in real-time. You can choose from simple progress bars, detailed built-in dashboards, or build your own custom monitoring solution.

## Built-in Dashboards

Built-in dashboards are the easiest way to monitor your pipeline. They use the `rich` library to provide beautiful, real-time terminal UIs with zero configuration.

### Dashboard Levels

| Option | What it Shows | Best For |
|--------|---------------|----------|
| `progress=True` | Minimal end-to-end progress bar | Simple scripts |
| `dashboard="compact"` | Single panel with rate, ETA, and progress | General use |
| `dashboard="detailed"` | Per-stage table and worker performance | Multi-stage pipelines |
| `dashboard="full"` | Everything + worker states + item tracker | Debugging and deep monitoring |

> [!NOTE]
> `dashboard="full"` works best when a `StatusTracker` is provided to track individual item history.

### Basic Usage

```python
import asyncio
from antflow import Pipeline

async def task(x):
    await asyncio.sleep(0.1)
    return x * 2

async def main():
    items = range(100)
    
    # 1. Simple progress bar
    await Pipeline.quick(items, task, workers=10, progress=True)

    # 2. Compact dashboard
    await Pipeline.quick(items, task, workers=10, dashboard="compact")

    # 3. Detailed dashboard (Recommended for multi-stage)
    await (
        Pipeline.create()
        .add("Fetch", task, workers=10)
        .add("Process", task, workers=5)
        .run(items, dashboard="detailed")
    )

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Event-Driven Monitoring (StatusTracker)

For logging, alerts, or reacting to specific events in real-time, use `StatusTracker` callbacks.

```python
import asyncio
from antflow import Pipeline, Stage, StatusTracker

async def on_status_change(event):
    if event.status == "failed":
        print(f"❌ Item {event.item_id} failed at {event.stage}: {event.metadata.get('error')}")
    elif event.status == "completed" and event.stage == "Save":
         print(f"✅ Item {event.item_id} fully processed")

async def main():
    tracker = StatusTracker(on_status_change=on_status_change)
    pipeline = Pipeline(
        stages=[Stage("Process", workers=5, tasks=[lambda x: x*2])],
        status_tracker=tracker
    )
    await pipeline.run(range(10))

if __name__ == "__main__":
    asyncio.run(main())
```

See the [StatusTracker API](../api/tracker.md) for task-level events like `on_task_retry` and `on_task_fail`.

---

## Snapshot API (Custom UIs)

If you are building your own UI (e.g., a web dashboard with FastAPI), you can query the pipeline state at any time using snapshots.

### Getting a Snapshot

```python
snapshot = pipeline.get_dashboard_snapshot()

print(f"Items processed: {snapshot.pipeline_stats.items_processed}")
print(f"Items failed: {snapshot.pipeline_stats.items_failed}")
print(f"Queue sizes: {snapshot.pipeline_stats.queue_sizes}")

# Worker states
for name, state in snapshot.worker_states.items():
    print(f"Worker {name} is {state.status}")
```

### Snapshot Structure

A `DashboardSnapshot` contains:
- **`worker_states`**: Dict of `WorkerState` (status, current item, duration)
- **`worker_metrics`**: Dict of `WorkerMetrics` (avg time, processed count, failures)
- **`pipeline_stats`**: Aggregate statistics and per-stage metrics
- **`timestamp`**: Snapshot generation time

---

## Advanced: Combining Polling and Events

You can manually poll the pipeline status while it runs in the background.

```python
import asyncio
from antflow import Pipeline

async def my_monitor(pipeline):
    while True:
        snapshot = pipeline.get_dashboard_snapshot()
        print(f"Monitoring: {snapshot.pipeline_stats.items_processed} items done")
        
        # Stop when pipeline is done (check your own condition)
        # OR just rely on cancelling this task when main pipeline finishes
        await asyncio.sleep(1.0)

async def main():
    pipeline = Pipeline(stages=[...])
    
    # Start monitor
    monitor_task = asyncio.create_task(my_monitor(pipeline))
    
    try:
        await pipeline.run(items)
    finally:
        monitor_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Custom Dashboards

You can create your own dashboard class by implementing the `DashboardProtocol`. This allows you to pass your own display logic directly into `pipeline.run()`.

```python
from antflow import DashboardProtocol

class MyLogDashboard:
    def on_start(self, pipeline, total_items):
        print(f"Starting {total_items} items")

    def on_update(self, snapshot):
        print(f"Progress: {snapshot.pipeline_stats.items_processed}")

    def on_finish(self, results, summary):
        print("Done!")

# Use it
await pipeline.run(items, custom_dashboard=MyLogDashboard())
```

For more details, see the [Custom Dashboard Guide](custom-dashboard.md).

---

## Examples

Check the `examples/` directory for full implementations:

- **[dashboard_levels.py](../examples/index.md#dashboards)**: Comparing compact, detailed, and full dashboards
- **[custom_dashboard.py](../examples/index.md#dashboards)**: Implementing a custom dashboard class
- **[web_dashboard/](../examples/index.md#dashboards)**: Complete FastAPI + WebSocket dashboard

## API Reference

- [Pipeline API](../api/pipeline.md) - `get_dashboard_snapshot()`
- [Display Module](../api/display.md) - Built-in dashboards and protocols
- [StatusTracker](../api/tracker.md) - Event-driven monitoring
