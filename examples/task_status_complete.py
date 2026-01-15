"""
Complete Example: Internal Task Status Updates

This comprehensive example demonstrates all aspects of using set_task_status()
to show real-time progress within long-running tasks.

Sections:
1. Basic Usage - Simple status updates
2. Real-World Polling - Simulating OpenAI batch processing
3. Rate Limiting - Controlling update frequency
4. Custom Dashboard - Full control over status display

Run this file to see all examples in action!
"""

import asyncio
import random
from rich.console import Console
from rich.table import Table
from antflow import Pipeline, Stage, set_task_status
from antflow.types import DashboardSnapshot, ErrorSummary, PipelineResult


# ============================================================================
# SECTION 1: Basic Usage
# ============================================================================

async def basic_example(filename: str) -> dict:
    """
    Simple example showing status updates through multiple steps.
    This is the most common use case.
    """
    set_task_status("🔍 Validating...")
    await asyncio.sleep(0.5)
    
    set_task_status("📖 Reading...")
    await asyncio.sleep(0.7)
    
    set_task_status("⚙️  Processing...")
    await asyncio.sleep(1.0)
    
    set_task_status("💾 Saving...")
    await asyncio.sleep(0.5)
    
    return {"file": filename, "status": "completed"}


# ============================================================================
# SECTION 2: Real-World Polling (OpenAI Batch Processing)
# ============================================================================

class FakeOpenAIAPI:
    """Simulates OpenAI batch API for demonstration"""
    
    def __init__(self):
        self.batches = {}
        self.call_count = {}
    
    async def upload(self, file_path: str) -> str:
        await asyncio.sleep(0.3)
        return f"file-{random.randint(1000, 9999)}"
    
    async def create_batch(self, file_id: str) -> str:
        await asyncio.sleep(0.2)
        batch_id = f"batch-{random.randint(1000, 9999)}"
        self.batches[batch_id] = {"status": "validating"}
        self.call_count[batch_id] = 0
        return batch_id
    
    async def retrieve(self, batch_id: str) -> dict:
        """
        Simulates polling - called MULTIPLE TIMES until completed.
        Each call returns a different status!
        """
        await asyncio.sleep(0.2)
        self.call_count[batch_id] += 1
        call_num = self.call_count[batch_id]
        
        # Status progression
        if call_num == 1:
            status = "validating"
        elif call_num <= 3:
            status = "in_progress"
        elif call_num == 4:
            status = "finalizing"
        else:
            status = "completed"
        
        return {"id": batch_id, "status": status}


fake_api = FakeOpenAIAPI()


async def realistic_polling_example(file_path: str) -> dict:
    """
    Real-world example: Upload file, poll status, download results.
    This is exactly how you'd use it with OpenAI's Batch API.
    """
    
    # Step 1: Upload
    set_task_status("⬆️  Uploading file...")
    file_id = await fake_api.upload(file_path)
    
    # Step 2: Create batch
    set_task_status("🚀 Creating batch...")
    batch_id = await fake_api.create_batch(file_id)
    
    # Step 3: Poll until complete (MULTIPLE API CALLS!)
    poll_count = 0
    while True:
        poll_count += 1
        
        # Call API (this happens multiple times!)
        response = await fake_api.retrieve(batch_id)
        status = response["status"]
        
        # Update dashboard with current status
        set_task_status(f"⏳ Poll #{poll_count}: {status}...")
        
        if status == "completed":
            break
        
        await asyncio.sleep(0.5)
    
    # Step 4: Download
    set_task_status("⬇️  Downloading results...")
    await asyncio.sleep(0.3)
    
    return {"file": file_path, "batch_id": batch_id, "status": "completed"}


# ============================================================================
# SECTION 3: Rate Limiting Strategies
# ============================================================================

async def rate_limiting_example(item: int) -> int:
    """
    Demonstrates different rate limiting strategies for tight loops.
    """
    
    # Strategy 1: Using min_interval parameter
    print(f"\n  [Item {item}] Strategy 1: Rate limiting with min_interval")
    for i in range(20):
        updated = set_task_status(f"Processing {i}/20...", min_interval=0.3)
        if updated:
            print(f"    ✓ Updated at iteration {i}")
        await asyncio.sleep(0.05)
    
    # Strategy 2: Manual control with modulo (more efficient)
    print(f"\n  [Item {item}] Strategy 2: Update every N iterations")
    for i in range(100):
        if i % 20 == 0:  # Update every 20 iterations
            set_task_status(f"Processing {i}/100...")
            print(f"    ✓ Updated at iteration {i}")
        await asyncio.sleep(0.01)
    
    set_task_status("✅ Completed!")
    return item * 2


# ============================================================================
# SECTION 4: Custom Dashboard
# ============================================================================

class CustomStatusDashboard:
    """
    Custom dashboard showing how to access WorkerState.current_task.
    Implements the DashboardProtocol interface.
    """
    
    def __init__(self):
        self.console = Console()
    
    def on_start(self, pipeline, total_items: int):
        self.console.print(f"\n[bold green]🚀 Starting {total_items} items[/bold green]\n")
    
    def on_update(self, snapshot: DashboardSnapshot):
        table = Table(title="Custom Dashboard", show_header=True)
        table.add_column("Worker", style="cyan", width=15)
        table.add_column("Status", style="yellow", width=8)
        table.add_column("Item", style="green", width=8)
        table.add_column("Internal Task Status", style="white", width=35)
        
        for worker_name, state in snapshot.worker_states.items():
            status_emoji = "🔵" if state.status == "busy" else "⚪"
            
            # Access current_task set by set_task_status()
            internal_status = state.current_task or "-"
            
            table.add_row(
                worker_name,
                f"{status_emoji} {state.status}",
                str(state.current_item_id) if state.current_item_id else "-",
                internal_status  # 👈 This shows set_task_status() updates!
            )
        
        # Summary
        stats = snapshot.pipeline_stats
        table.add_section()
        table.add_row(
            "[bold]SUMMARY[/bold]",
            "",
            f"✅ {stats.items_processed}",
            f"In-flight: {stats.items_in_flight}"
        )
        
        self.console.clear()
        self.console.print(table)
    
    def on_finish(self, results: list[PipelineResult], summary: ErrorSummary):
        self.console.print(f"\n[bold green]✅ Completed {len(results)} items![/bold green]\n")


# ============================================================================
# MAIN: Run all examples
# ============================================================================

async def main():
    print("=" * 80)
    print("COMPLETE EXAMPLE: Internal Task Status Updates")
    print("=" * 80)
    
    # ========================================================================
    # Example 1: Basic Usage
    # ========================================================================
    print("\n" + "▶️  " + "=" * 74)
    print("EXAMPLE 1: Basic Usage (Simple Status Updates)")
    print("=" * 80)
    print("Watch the 'Current Task' column in the dashboard below.\n")
    
    pipeline1 = Pipeline.create().add("Process", basic_example, workers=2).build()
    await pipeline1.run([f"file_{i}.txt" for i in range(1, 4)], dashboard="detailed")
    
    # ========================================================================
    # Example 2: Real-World Polling
    # ========================================================================
    print("\n" + "▶️  " + "=" * 74)
    print("EXAMPLE 2: Real-World Polling (OpenAI Batch Processing)")
    print("=" * 80)
    print("Notice how the status changes during polling (multiple API calls).\n")
    
    # Using Stage for more control
    stage = Stage(
        name="OpenAI Batch",
        workers=2,
        tasks=[realistic_polling_example],
        task_attempts=3
    )
    pipeline2 = Pipeline(stages=[stage])
    await pipeline2.run([f"doc_{i}.jsonl" for i in range(1, 4)], dashboard="detailed")
    
    # ========================================================================
    # Example 3: Rate Limiting
    # ========================================================================
    print("\n" + "▶️  " + "=" * 74)
    print("EXAMPLE 3: Rate Limiting Strategies")
    print("=" * 80)
    print("Demonstrates different ways to control update frequency.\n")
    
    pipeline3 = Pipeline.create().add("RateLimit", rate_limiting_example, workers=1).build()
    await pipeline3.run([1], dashboard="detailed")
    
    # ========================================================================
    # Example 4: Custom Dashboard
    # ========================================================================
    print("\n" + "▶️  " + "=" * 74)
    print("EXAMPLE 4: Custom Dashboard")
    print("=" * 80)
    print("Shows how to access current_task in a custom dashboard.\n")
    
    custom_dash = CustomStatusDashboard()
    pipeline4 = Pipeline.create().add("Custom", basic_example, workers=3).build()
    await pipeline4.run([f"item_{i}.txt" for i in range(1, 6)], custom_dashboard=custom_dash)
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 80)
    print("📚 KEY TAKEAWAYS:")
    print("=" * 80)
    print("""
1. Basic Usage:
   set_task_status("Processing...")  # Simple and effective

2. Polling (Multiple API Calls):
   while not done:
       status = await api.check_status()
       set_task_status(f"Polling: {status}...")  # Updates each iteration!

3. Rate Limiting:
   # Option A: Automatic
   set_task_status("...", min_interval=0.5)  # Max 2 updates/second
   
   # Option B: Manual (more efficient)
   if i % 50 == 0:
       set_task_status(f"Processing {i}/1000...")

4. Custom Dashboard:
   def on_update(self, snapshot):
       for worker, state in snapshot.worker_states.items():
           print(state.current_task)  # Access the status!
""")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
