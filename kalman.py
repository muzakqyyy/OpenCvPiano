# kalman.py
# Kalman scalar ringan untuk smoothing skor kontinu.

class ScalarKalmanFilter:
    def __init__(
        self,
        process_variance: float = 1e-4,
        measurement_variance: float = 1e-2,
        initial_estimate: float = 0.0,
        initial_error: float = 1.0,
    ):
        self.q = process_variance
        self.r = measurement_variance
        self.x = initial_estimate
        self.p = initial_error

    def update(self, measurement: float | None) -> float:
        if measurement is None:
            return self.x

        self.p += self.q
        k = self.p / (self.p + self.r)
        self.x = self.x + k * (measurement - self.x)
        self.p = (1.0 - k) * self.p
        return self.x