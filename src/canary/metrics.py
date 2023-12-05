import time
import collections

from prometheus_client import Gauge

class EventWindowGauge:

    def __init__(self, name: str, documentation: str, labelnames: list, window: float):
        self.queue = collections.deque()
        self.window = max(1., float(window))
        self.metric = Gauge(
            name=name,
            documentation=documentation,
            labelnames=labelnames
        )

    def update(self, labels: dict):
        # Get the current timestamp
        timestamp = time.time()

        # Add the current time to the right end of the sample queue
        self.queue.append(timestamp)

        # Pop all samples off the queue that are older than our time window
        while len(self.queue) > 0:
            if (self.queue[0] + self.window) < timestamp:
                self.queue.popleft()

        # Metric is the number of samples currently in the queue within the time window
        self.metric.labels(**labels).set(len(self.queue))
