"""
Fast flashover fire profile.
Near-step function: temperature spikes from 25C to 200C+ in ~5s.
"""

import time
import math

class FlashoverProfile:
    def __init__(self):
        self.t0 = None
        self.max_temp = 250.0
        self.max_smoke = 3000.0
        self.growth_rate = 1.2

    def start(self):
        self.t0 = time.time()

    def get_readings(self, now=None):
        if now is None:
            now = time.time()
        if self.t0 is None:
            self.t0 = now
        t = now - self.t0

        temp = 25.0 + self.max_temp / (1.0 + math.exp(-self.growth_rate * (t - 5.0)))
        smoke = 50.0 + self.max_smoke / (1.0 + math.exp(-self.growth_rate * (t - 3.0)))
        flame = 1.0 if t > 2.0 else 0.0

        return {"temp_c": round(temp, 1), "smoke_ppm": round(smoke, 0),
                "flame_detected": bool(flame)}
