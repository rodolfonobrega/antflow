# Progress Bar Guide

AntFlow provides built-in progress visualization options that require zero configuration.

## Quick Start

The simplest way to add progress visualization is with the `progress=True` flag:

```python
import asyncio
from antflow import Pipeline

async def task(x):
    return x * 2

async def main():
    results = await Pipeline.quick(range(100), task, workers=10, progress=True)

if __name__ == "__main__":
    asyncio.run(main())
```

This displays a minimal progress bar in your terminal:

```
[████████████░░░░░░░░░░░░░░░░░░] 42% | 126/300 | 24.5/s | 2 failed
```

## Dashboard Options

For more detailed monitoring, use the `dashboard` parameter:

```python
import asyncio
from antflow import Pipeline

async def task(x):
    await asyncio.sleep(0.01)
    return x * 2

async def main():
    items = range(100)
    # Use: "compact", "detailed", or "full"
    results = await Pipeline.quick(items, task, workers=5, dashboard="detailed")

if __name__ == "__main__":
    asyncio.run(main())
```

### Compact Dashboard

Shows a single panel with:

- Progress bar
- Current stage activity
- Processing rate and ETA
- Success/failure counts

```
╭───────────────── AntFlow Pipeline ─────────────────╮
│  [████████████░░░░░░░░░░░░░░░░░░] 42%              │
│  Stage: Process (3/5 workers busy)                 │
│  Rate: 24.5 items/sec | ETA: 00:02:15              │
│  OK: 126 | Failed: 2 | Remaining: 172              │
╰────────────────────────────────────────────────────╯
```

### Detailed Dashboard

Shows:

- Overall progress bar with rate and ETA
- Per-stage progress table with worker counts
- Worker performance metrics

### Full Dashboard

The most comprehensive option, showing:

- Overview statistics
- Stage metrics
- Individual worker monitoring
- Item tracking (requires `StatusTracker`)

For item tracking, add a `StatusTracker`:

```python
import asyncio
from antflow import Pipeline, StatusTracker

async def task(x):
    return x

async def main():
    tracker = StatusTracker()
    results = await (
        Pipeline.create()
        .add("Process", task, workers=5)
        .with_tracker(tracker)
        .run(range(50), dashboard="full")
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## Using with Pipeline.quick()

Progress works with all Pipeline APIs:

```python
# With quick()
results = await Pipeline.quick(items, process, workers=10, progress=True)

# With dashboard
results = await Pipeline.quick(
    items,
    [fetch, process, save],
    workers=5,
    dashboard="compact"
)
```

## Using with Builder API

```python
results = await (
    Pipeline.create()
    .add("Fetch", fetch, workers=10)
    .add("Process", process, workers=5)
    .run(items, dashboard="detailed")
)
```

## Note on Mutual Exclusion

You cannot use both `progress=True` and `dashboard` at the same time:

```python
# This will raise ValueError
results = await pipeline.run(items, progress=True, dashboard="compact")
```

Choose one or the other based on your needs.
