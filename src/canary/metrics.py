import logging
import time
import collections

from aiohttp import web
from prometheus_client import Gauge


class MetricServer:

    def __init__(self, window: float):
        self.metrics = dict()
        self.window = max(1., float(window))

    async def add(self, metric: str, labels: dict, value: float):

        timestamp = time.time()

        key = (metric, str(labels))
        self.metrics[key] = dict(
            timestamp=timestamp,
            metric=metric,
            labels=labels,
            value=value
        )

        # Remove expired metrics
        for key in list(self.metrics.keys()):
            metric = self.metrics[key]
            if (metric["timestamp"] + self.window) < timestamp:
                del self.metrics[key]

    async def render(self):

        logging.info("rendering metrics")

        timestamp = time.time()

        # Remove expired metrics
        for key in list(self.metrics.keys()):
            metric = self.metrics[key]
            if (metric["timestamp"] + self.window) < timestamp:
                del self.metrics[key]

        def format_metric(metric: dict):

            def format_label(kv):
                key, value = kv
                return f"{key}=\"{value}\""

            label_str = ",".join(map(format_label, metric["labels"].items()))

            return f"""
            TYPE {metric['metric']} gauge
            {metric['metric']}{{{label_str}}} {metric['value']}
            """

        return "\n".join(map(format_metric, self.metrics.values()))

    async def serve(self, request):
        logging.info("serving metrics")
        return web.Response(text=await self.render())


async def start_metric_server(window: float, port: int = 8080):

    server = MetricServer(window=window)

    logging.info("starting http metrics server")
    app = web.Application()
    app.add_routes([
        web.get('/metrics', server.serve)
    ])

    logging.info("starting http metrics server runner")
    runner = web.AppRunner(app)
    await runner.setup()

    logging.info("starting http metrics server site")
    site = web.TCPSite(runner, 'localhost', port)
    await site.start()

    return server


class EventWindowGauge:

    def __init__(self, name: str, documentation: str, labelnames: list, window: float):
        self.queues = dict()
        self.window = max(1., float(window))
        self.metric = Gauge(
            name=name,
            documentation=documentation,
            labelnames=labelnames,
            multiprocess_mode="mostrecent"
        )

    def update(self, labels: dict, append: bool = False):
        # Get the current timestamp
        timestamp = time.time()

        labels_str = str(labels)
        if labels_str not in self.queues:
            self.queues[labels_str] = collections.deque()
        queue = self.queues[labels_str]

        # Add the current time to the right end of the sample queue
        if append:
            queue.append(timestamp)

        # Pop all samples off the queue that are older than our time window
        while (len(queue) > 0) and ((queue[0] + self.window) < timestamp):
            queue.popleft()

        # Metric is the number of samples currently in the queue within the time window
        self.metric.labels(**labels).set(len(queue))
