import asyncio
import aiohttp
import time
import json
import statistics
import os
import signal

# API URL and controls
URL = "https://www.aimadlab.com/api/click-count/add"
# NUM_REQUESTS = 1000     # Number of requests to send
NUM_REQUESTS = float('inf')  # Run forever
CHECK_INTERVAL = 0.11  # How often to check for completed requests (seconds)

# Global variables
shutdown = False
last_counter = None

def signal_handler(signum, frame):
    global shutdown
    print("\nGraceful shutdown initiated... Completing current requests...")
    shutdown = True

async def send_request(session, index):
    global last_counter
    try:
        if shutdown:
            return None

        timestamp = time.time()
        async with session.get(URL) as response:
            text = await response.text()
            counter = json.loads(text)['data']

            # Calculate increase from last counter
            increase = '?' if last_counter is None else counter - last_counter
            increase_str = f"+{increase}" if isinstance(increase, int) and increase > 0 else str(increase)

            print(f"Request {index+1}/{NUM_REQUESTS} - Time: {timestamp:.3f}, Counter = {counter} ({increase_str})")

            last_counter = counter
            return timestamp, counter
    except Exception as e:
        print(f"Request {index+1}/{NUM_REQUESTS} failed: {e}")
        return None

def analyze_results(results, start_time, end_time):
    print("\n=== ANALYSIS ===")

    # Overall Statistics
    total_time = end_time - start_time
    requests_sent = len(results)
    print(f"\n1. Overall Statistics:")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Requests sent: {requests_sent}/{NUM_REQUESTS if NUM_REQUESTS != float('inf') else 'inf'}")
    print(f"Average requests per second: {requests_sent/total_time:.2f}")

    # Counter Increases
    print(f"\n2. Counter Progress:")
    initial_counter = results[0][1] - 1  # Subtract 1 to show true starting value
    final_counter = results[-1][1]
    total_increase = final_counter - initial_counter  # No need for +1 now since we adjusted initial_counter
    expected_increases = requests_sent
    print(f"Starting counter: {initial_counter}")
    print(f"Final counter: {final_counter}")
    print(f"Total increase: {total_increase}")
    print(f"Success rate: {(total_increase/expected_increases)*100:.1f}%")

    # Time Intervals Analysis
    print(f"\n3. Time Intervals Between Requests:")
    intervals = []
    for i in range(1, len(results)):
        prev_time, prev_counter = results[i-1]
        curr_time, curr_counter = results[i]
        interval = curr_time - prev_time
        intervals.append(interval)

    print(f"Average interval: {statistics.mean(intervals):.3f}s")
    print(f"Min interval: {min(intervals):.3f}s")
    print(f"Max interval: {max(intervals):.3f}s")
    print(f"Median interval: {statistics.median(intervals):.3f}s")

    # Counter Increase Pattern
    print(f"\n4. Counter Increase Patterns:")
    print(f"Successful increases: {requests_sent}")  # All requests increase
    if intervals:
        print(f"Average time between increases: {statistics.mean(intervals):.3f}s")
        print(f"Min time between increases: {min(intervals):.3f}s")
        print(f"Max time between increases: {max(intervals):.3f}s")

async def main():
    signal.signal(signal.SIGINT, signal_handler)
    os.system('cls' if os.name == 'nt' else 'clear')

    print(f"Starting {NUM_REQUESTS} requests (checking every {CHECK_INTERVAL}s)...")
    print("Press Ctrl+C for graceful shutdown with analysis\n")

    connector = aiohttp.TCPConnector()
    async with aiohttp.ClientSession(connector=connector) as session:
        results = []
        start_time = time.time()
        i = 0
        pending = set()

        while not shutdown and (i < NUM_REQUESTS or NUM_REQUESTS == float('inf')):
            task = asyncio.create_task(send_request(session, i))
            pending.add(task)
            i += 1

            done, pending = await asyncio.wait(pending, timeout=CHECK_INTERVAL)
            for task in done:
                result = await task
                if result:
                    results.append(result)

            if shutdown:
                break

        if pending:
            done, _ = await asyncio.wait(pending)
            for task in done:
                result = await task
                if result:
                    results.append(result)

        end_time = time.time()
        analyze_results(results, start_time, end_time)

asyncio.run(main())