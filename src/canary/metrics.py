import logging
import time
import collections

from prometheus_client import Gauge


class EventWindowGauge:

    def __init__(self, name: str, documentation: str, labelnames: list, window: float):
        self.queues = dict()
        self.window = max(1., float(window))
        self.metric = Gauge(
            name=name,
            documentation=documentation,
            labelnames=labelnames,
            multiprocess_mode="livemostrecent"
        )

    def update(self, labels: dict):
        # Get the current timestamp
        timestamp = time.time()

        labels_str = str(labels)
        if labels_str not in self.queues:
            self.queues[labels_str] = collections.deque()
        queue = self.queues[labels_str]

        # Add the current time to the right end of the sample queue
        queue.append(timestamp)

        # Pop all samples off the queue that are older than our time window
        while (len(queue) > 0) and ((queue[0] + self.window) < timestamp):
            queue.popleft()

        # Metric is the number of samples currently in the queue within the time window
        self.metric.labels(**labels).set(len(queue))
