# Writing a program that uses exactly 50% CPU utilization

In one of my project, we needed to add noisy neighbor process. And apparently it was not very straightforward how it should be. The first program was simply alternating between doing work and sleeping for equal amounts of time. 

- **Busy wait for 1 millisecond** - keeping the CPU at 100% utilization
- **Sleep for 1 millisecond** - letting the CPU rest at 0% utilization

It logically should achieve 50% CPU utilization. However, it does not.


Python code

```python
import time
from datetime import datetime

i = 0
while True:
    if i % 2 == 0:
        sleep_in_ms = 1
        sleep_in_second = sleep_in_ms * 0.001
        time.sleep(sleep_in_second)  # Sleep for 1ms
    else:
        start_time_ms = int(datetime.now().timestamp() * 1000)
        while True:
            current_time_ms = datetime.now().timestamp() * 1000
            busy_wait_duration = current_time_ms - start_time_ms
            if busy_wait_duration > sleep_in_ms:  # Busy wait for 1ms
                break
    i += 1
```

The program alternates between sleeping and busy-waiting, each for exactly 1 millisecond. Too simple to think.  
However, apparently if you run the program, you will see **37%** not 50%.

Where did that missing 13% go?

I overlooked some factors that affects the CPU utilization other than my code itself.
There are overall four different additional factors outside of your code logic that can affect the CPU utilization.

### 1. The Overhead Tax
Every operation in the program—checking the time, evaluating conditions, managing the loop—consumes CPU cycles. This overhead isn't accounted for in my 1ms calculations. While individually tiny, these operations accumulate and eat into what should be "productive" busy-wait time.

### 2. Sleep Function Inaccuracy
The `time.sleep()` function doesn't provide microsecond precision. Operating systems typically have minimum sleep granularities, often much larger than 1 millisecond. When I requested a 1ms sleep, the actual sleep duration was frequently longer, skewing the balance toward more idle time.

### 3. Operating System Scheduling
Modern operating systems use complex scheduling algorithms. When my process wakes up from sleep, there's no guarantee it will immediately resume execution. The scheduler might introduce additional delays, further reducing the actual busy-wait time.

### 4. System Interference
Other processes, system activities, and even hardware interrupts can influence how much CPU time my process actually receives, making precise control nearly impossible.


## Solution
...