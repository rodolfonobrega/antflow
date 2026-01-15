import asyncio
from antflow import Pipeline, Stage

async def upload(item):
    """
    This task simulates an API upload with a strict rate limit.
    Even with 50 workers, only 2 will be inside this function at once.
    """
    print(f"  [UP] Starting upload for item {item}...")
    await asyncio.sleep(0.5) # Simulate network I/O
    return item

async def poll(item):
    """
    This task simulates a long-running monitoring process.
    All 50 workers can be here simultaneously.
    """
    print(f"  [POLL] Monitoring item {item} on OpenAI status...")
    await asyncio.sleep(2.0) # Simulate a long wait for the remote job
    return f"Result_{item}"

async def main():
    print("=" * 60)
    print("OpenAI Batch Processing Example: Task Concurrency Limits")
    print("=" * 60)
    print("\nScenario:")
    print("  - We have 50 workers to monitor many concurrent jobs.")
    print("  - But OpenAI only allows 2 uploads at the same time.")
    print("\nBehavior:")
    print("  - Uploads will happen in pairs (throttled by limit).")
    print("  - Polling will accumulate up to 50 active items.")
    print("-" * 60)

    # Configure the stage
    stage = Stage(
        name="OpenAI_Batch",
        workers=50, # High capacity for the long polling wait
        tasks=[upload, poll],
        task_concurrency_limits={
            "upload": 2 # STRICT LIMIT: Only 2 concurrent uploads
        }
    )

    # Build and run the pipeline
    pipeline = Pipeline(stages=[stage])
    
    # Process 10 items to demonstrate the pattern clearly
    results = await pipeline.run(range(10), progress=True)
    
    print(f"\n✅ Finished! {len(results)} items processed.")
    for res in results:
        print(f"  - Item {res.id}: {res.value}")

if __name__ == "__main__":
    asyncio.run(main())
