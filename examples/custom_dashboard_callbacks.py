"""
Custom Dashboard with Callbacks (Event-Driven) Example

This example demonstrates how to build a custom dashboard using StatusTracker callbacks
instead of polling with DashboardProtocol. This is the event-driven alternative to
the polling-based custom_dashboard.py example.

Key Differences:
- DashboardProtocol (Polling): on_update() called every 0.1s (configurable)
- StatusTracker (Callbacks): Events fired immediately when status changes

When to use each:
- Callbacks: Real-time logging, alerts, event streaming, lower latency
- Polling: Terminal UIs, web dashboards, periodic aggregation
"""

import asyncio
import json
import random
import sys
from datetime import datetime
from typing import Dict

from antflow import Pipeline, Stage, StatusTracker, StatusEvent, TaskEvent


async def process_item(x: int) -> dict:
    """Simulate processing with variable delay."""
    await asyncio.sleep(random.uniform(0.1, 0.3))
    if random.random() < 0.1:
        raise ValueError("Random error")
    return {"id": x, "result": x * 2}


async def fetch_item(x: int) -> dict:
    """Fetch stage: int → dict."""
    await asyncio.sleep(random.uniform(0.05, 0.15))
    return {"id": x, "data": f"raw_{x}"}


async def transform_item(item: dict) -> dict:
    """Transform stage: dict → dict."""
    await asyncio.sleep(random.uniform(0.05, 0.1))
    if random.random() < 0.1:
        raise ValueError("Random error")
    item["transformed"] = True
    return item


async def save_item(item: dict) -> str:
    """Save stage: dict → str."""
    await asyncio.sleep(random.uniform(0.03, 0.08))
    return f"saved_{item['id']}"


class SimpleCallbackDashboard:
    """
    Minimal dashboard using callbacks instead of polling.
    
    Equivalent to SimpleDashboard from custom_dashboard.py but event-driven.
    """
    
    def __init__(self, total_items: int):
        self.total = total_items
        self.completed = 0
        self.failed = 0
        self.in_progress = 0
    
    async def on_status_change(self, event: StatusEvent):
        """Called on every status change - no polling needed!"""
        if event.status == "in_progress":
            self.in_progress += 1
        elif event.status == "completed":
            self.in_progress -= 1
            self.completed += 1
        elif event.status == "failed":
            self.in_progress -= 1
            self.failed += 1
        
        # Update display
        pct = (self.completed / self.total * 100) if self.total else 0
        sys.stdout.write(
            f"\r[{datetime.now().strftime('%H:%M:%S')}] "
            f"Progress: {pct:5.1f}% | "
            f"Done: {self.completed} | "
            f"Failed: {self.failed} | "
            f"In flight: {self.in_progress}   "
        )
        sys.stdout.flush()


class JSONCallbackDashboard:
    """
    JSON event stream using callbacks.
    
    Equivalent to JSONDashboard from custom_dashboard.py but event-driven.
    Each status change generates a JSON event immediately.
    """
    
    def __init__(self, output_file=None):
        self.output_file = output_file
        self.events = []
        self.stats = {"completed": 0, "failed": 0, "in_progress": 0}
    
    def _emit(self, event):
        self.events.append(event)
        if self.output_file:
            with open(self.output_file, "w") as f:
                json.dump(self.events, f, indent=2)
        else:
            print(json.dumps(event))
    
    async def on_status_change(self, event: StatusEvent):
        """Emit JSON for each status change."""
        # Update internal stats
        if event.status == "in_progress":
            self.stats["in_progress"] += 1
        elif event.status == "completed":
            self.stats["in_progress"] -= 1
            self.stats["completed"] += 1
        elif event.status == "failed":
            self.stats["in_progress"] -= 1
            self.stats["failed"] += 1
        
        # Emit event
        self._emit({
            "type": "status_change",
            "timestamp": datetime.now().isoformat(),
            "item_id": event.item_id,
            "stage": event.stage,
            "status": event.status,
            "worker": event.worker,
            "current_stats": dict(self.stats),
        })


class MultiStageCallbackDashboard:
    """
    Multi-stage dashboard using callbacks.
    
    Tracks per-stage progress using events instead of polling.
    """
    
    def __init__(self, total_items: int, stages: list):
        self.total = total_items
        self.stages = stages
        self.stage_stats = {
            stage: {"pending": 0, "in_progress": 0, "completed": 0, "failed": 0}
            for stage in stages
        }
    
    async def on_status_change(self, event: StatusEvent):
        """Update stage stats on each event."""
        if event.stage not in self.stage_stats:
            return
        
        stats = self.stage_stats[event.stage]
        
        if event.status == "queued":
            stats["pending"] += 1
        elif event.status == "in_progress":
            stats["pending"] -= 1
            stats["in_progress"] += 1
        elif event.status == "completed":
            stats["in_progress"] -= 1
            stats["completed"] += 1
        elif event.status == "failed":
            stats["in_progress"] -= 1
            stats["failed"] += 1
        
        # Render (similar to polling version but triggered by events)
        self._render()
    
    def _render(self):
        """Render the dashboard."""
        total_completed = sum(s["completed"] + s["failed"] for s in self.stage_stats.values())
        pct = (total_completed / (self.total * len(self.stages)) * 100) if self.total else 0
        
        bar_width = 30
        filled = int(bar_width * total_completed / (self.total * len(self.stages))) if self.total else 0
        bar = "█" * filled + "░" * (bar_width - filled)
        
        lines = [
            f"Overall: [{bar}] {pct:5.1f}%",
            "",
            f"{'Stage':<12} {'Pending':>8} {'Active':>8} {'Done':>8} {'Failed':>8}",
            "-" * 50,
        ]
        
        for stage_name, stats in self.stage_stats.items():
            lines.append(
                f"{stage_name:<12} "
                f"{stats['pending']:>8} "
                f"{stats['in_progress']:>8} "
                f"{stats['completed']:>8} "
                f"{stats['failed']:>8}"
            )
        
        sys.stdout.write("\r" + "\033[K" + "\n".join(lines) + "\033[F" * (len(lines) - 1))
        sys.stdout.flush()


class TaskLevelMonitor:
    """
    Advanced monitoring with task-level callbacks.
    
    Shows the power of callbacks: you can react to individual task events
    (start, complete, retry, fail) which is impossible with polling.
    """
    
    def __init__(self):
        self.task_stats: Dict[str, Dict[str, int]] = {}
    
    async def on_task_start(self, event: TaskEvent):
        """Called when a task starts."""
        if event.task_name not in self.task_stats:
            self.task_stats[event.task_name] = {
                "started": 0, "completed": 0, "retries": 0, "failed": 0
            }
        self.task_stats[event.task_name]["started"] += 1
    
    async def on_task_complete(self, event: TaskEvent):
        """Called when a task completes successfully."""
        if event.task_name in self.task_stats:
            self.task_stats[event.task_name]["completed"] += 1
    
    async def on_task_retry(self, event: TaskEvent):
        """Called when a task is retrying."""
        if event.task_name in self.task_stats:
            self.task_stats[event.task_name]["retries"] += 1
        print(f"⚠️  Task {event.task_name} retry #{event.attempt} for item {event.item_id}")
    
    async def on_task_fail(self, event: TaskEvent):
        """Called when a task fails after all retries."""
        if event.task_name in self.task_stats:
            self.task_stats[event.task_name]["failed"] += 1
        print(f"❌ Task {event.task_name} FAILED for item {event.item_id}")
    
    def print_summary(self):
        """Print final task statistics."""
        print("\n\nTask-Level Statistics:")
        print(f"{'Task':<20} {'Started':>10} {'Completed':>10} {'Retries':>10} {'Failed':>10}")
        print("-" * 62)
        for task_name, stats in self.task_stats.items():
            print(
                f"{task_name:<20} "
                f"{stats['started']:>10} "
                f"{stats['completed']:>10} "
                f"{stats['retries']:>10} "
                f"{stats['failed']:>10}"
            )


async def example_1_simple():
    """Example 1: Simple callback dashboard."""
    print("\n1. Simple Callback Dashboard:")
    print("-" * 40)
    print("Updates in real-time on every status change (no polling)\n")
    
    items = list(range(20))
    dashboard = SimpleCallbackDashboard(total_items=len(items))
    
    tracker = StatusTracker(on_status_change=dashboard.on_status_change)
    
    pipeline = Pipeline(
        stages=[
            Stage(name="Process", workers=3, tasks=[process_item], task_attempts=2)
        ],
        status_tracker=tracker,
    )
    
    results = await pipeline.run(items)
    print(f"\n   Complete! {len(results)} succeeded")


async def example_2_json():
    """Example 2: JSON event stream."""
    print("\n2. JSON Callback Dashboard (Event Stream):")
    print("-" * 40)
    print("Each status change generates a JSON event immediately\n")
    
    items = list(range(10))
    dashboard = JSONCallbackDashboard()
    
    tracker = StatusTracker(on_status_change=dashboard.on_status_change)
    
    pipeline = Pipeline(
        stages=[
            Stage(name="Process", workers=3, tasks=[process_item], task_attempts=2)
        ],
        status_tracker=tracker,
    )
    
    results = await pipeline.run(items)
    print(f"\n   Total events emitted: {len(dashboard.events)}")
    print(f"   Final stats: {dashboard.stats}")


async def example_3_multistage():
    """Example 3: Multi-stage callback dashboard."""
    print("\n3. Multi-Stage Callback Dashboard:")
    print("-" * 40)
    print("Tracks per-stage progress using events\n")
    
    items = list(range(20))
    stages = ["Fetch", "Transform", "Save"]
    
    dashboard = MultiStageCallbackDashboard(total_items=len(items), stages=stages)
    
    tracker = StatusTracker(on_status_change=dashboard.on_status_change)
    
    pipeline = Pipeline(
        stages=[
            Stage(name="Fetch", workers=3, tasks=[fetch_item], task_attempts=2),
            Stage(name="Transform", workers=2, tasks=[transform_item], task_attempts=2),
            Stage(name="Save", workers=2, tasks=[save_item], task_attempts=2),
        ],
        status_tracker=tracker,
    )
    
    results = await pipeline.run(items)
    print("\n" * 6)
    print(f"Complete! {len(results)} succeeded")


async def example_4_task_level():
    """Example 4: Task-level monitoring (only possible with callbacks!)."""
    print("\n4. Task-Level Monitoring:")
    print("-" * 40)
    print("Monitor individual task events - impossible with polling!\n")
    
    items = list(range(15))
    monitor = TaskLevelMonitor()
    
    tracker = StatusTracker(
        on_task_start=monitor.on_task_start,
        on_task_complete=monitor.on_task_complete,
        on_task_retry=monitor.on_task_retry,
        on_task_fail=monitor.on_task_fail,
    )
    
    pipeline = Pipeline(
        stages=[
            Stage(name="Process", workers=3, tasks=[process_item], task_attempts=2)
        ],
        status_tracker=tracker,
    )
    
    results = await pipeline.run(items)
    monitor.print_summary()


async def main():
    print("=" * 60)
    print("Custom Dashboard with Callbacks (Event-Driven)")
    print("=" * 60)
    print("\nThis example shows how to build dashboards using StatusTracker")
    print("callbacks instead of DashboardProtocol polling.")
    print("\nKey Advantage: Events fire immediately when status changes,")
    print("no need to poll every 0.1s!")
    
    await example_1_simple()
    await example_2_json()
    await example_3_multistage()
    await example_4_task_level()
    
    print("\n" + "=" * 60)
    print("Comparison: Callbacks vs Polling")
    print("=" * 60)
    print("\n✅ Callbacks (StatusTracker):")
    print("   - Events fire immediately (lower latency)")
    print("   - No polling overhead")
    print("   - Access to task-level events (start, retry, fail)")
    print("   - Best for: logging, alerts, event streaming")
    print("\n✅ Polling (DashboardProtocol):")
    print("   - Periodic snapshots (default: every 0.1s)")
    print("   - Complete state view")
    print("   - Simpler for terminal UIs")
    print("   - Best for: dashboards, periodic metrics")
    print("\n💡 You can use BOTH together for maximum flexibility!")


if __name__ == "__main__":
    asyncio.run(main())
