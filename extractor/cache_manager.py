import json
import os

CACHE_FILE = "cache.json"
CACHE = {}

# Load cache on start
def load_cache():
    global CACHE
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            CACHE = json.load(f)
    else:
        CACHE = {}

# Save cache
def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(CACHE, f, indent=2)

# Get from cache
def get_cache(key):
    return CACHE.get(key)

# Set cache
def set_cache(key, value):
    CACHE[key] = value
    save_cache()