import time
import logging
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def rate_limited(max_per_second):
    min_interval = 1.0 / max_per_second
    def decorator(func):
        last_time_called = [0.0]
        @wraps(func)
        def rate_limited_function(*args, **kwargs):
            elapsed = time.time() - last_time_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            result = func(*args, **kwargs)
            last_time_called[0] = time.time()
            return result
        return rate_limited_function
    return decorator

# Example usage
@rate_limited(5)  # Limit to 5 calls per second
def my_function():
    print("Function call")

if __name__ == "__main__":
    for _ in range(10):
        my_function()
