import time

import numpy as np

from parametric import BaseParams


# Create a class with a single numpy array field
class ArrayParams(BaseParams):
    array: np.ndarray[int]


# Generate random 1000x1000 array
big_array = np.random.randint(0, 100, size=(100000, 1000))

# Time direct numpy save
start_time = time.time()
np.save("big_array.npy", big_array)
np_save_time = time.time() - start_time

# Time direct numpy load
start_time = time.time()
loaded_np_array = np.load("big_array.npy")
np_load_time = time.time() - start_time

# Time BaseParams msgpack save
params = ArrayParams(array=big_array)
start_time = time.time()
params.save_msgpack("params.msgpack")
msgpack_save_time = time.time() - start_time

# Time BaseParams msgpack load
start_time = time.time()
loaded_params = ArrayParams.load_from_msgpack_path("params.msgpack")
msgpack_load_time = time.time() - start_time

# Print results
print("\nTiming Results (seconds):")
print(f"{'Operation':<25} {'Time':>10}")
print("-" * 35)
print(f"{'Numpy direct save':<25} {np_save_time:>10.4f}")
print(f"{'Numpy direct load':<25} {np_load_time:>10.4f}")
print(f"{'BaseParams msgpack save':<25} {msgpack_save_time:>10.4f}")
print(f"{'BaseParams msgpack load':<25} {msgpack_load_time:>10.4f}")

# Verify arrays are equal
assert np.array_equal(big_array, loaded_np_array)
assert np.array_equal(big_array, loaded_params.array)
