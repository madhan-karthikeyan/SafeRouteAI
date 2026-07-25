"""
Slow smolder fire profile.
Logistic growth: temperature and smoke rise gradually over ~60s.
Starts at baseline, reaches near-maximum after ~60 seconds.
"""

import math
import time

class SlowSmolderProfile:
    def __init__(self):
        self.t0 = None
        self.max_temp = 65.0
        self.max_smoke = 800.0
        self.growth_rate = 0.08
        self.t_offset = 60.0

    def start(self):
        self.t0 = time.time()

    def get_readings(self, now=None):
        if now is None:
            now = time.time()
        if self.t0 is None:
            self.t0 = now
        t = now - self.t0

        logistic_temp = self.max_temp / (1.0 + math.exp(-self.growth_rate * (t - self.t_offset)))
        logistic_smoke = self.max_smoke / (1.0 + math.exp(-self.growth_rate * (t - (self.t_offset - 5))))
        temp = 25.0 + logistic_temp
        smoke = logistic_smoke
        flame = 1.0 if t > 50.0 else 0.0

        return {"temp_c": round(temp, 1), "smoke_ppm": round(smoke, 0),
                "flame_detected": bool(flame)}
