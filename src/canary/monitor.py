import logging
import asyncio
import aiohttp
import urllib.parse
from prometheus_client import Gauge

from .metrics import EventWindowGauge

MIN_MONITOR_INTERVAL = 5  # seconds

LABELS = [
    "k8s_node_name",
    "k8s_pod_name",
    "k8s_pod_namespace",
    "monitor",
    "url"
]

# STATUS_LASTSEEN_GAUGE = Gauge(
#     name="canary_status_lastseen",
#     documentation="Timestamp of the most recent time a status code was observed.",
#     labelnames=LABELS+["status"],
# )
# UNHEALTHY_LASTSEEN_GAUGE = Gauge(
#     name="canary_unhealthy_lastseen",
#     documentation="Timestamp of the most recent time a monitor was unhealthy.",
#     labelnames=LABELS,
# )
# UNHEALTHY_EVENT_GAUGES = [
#     EventWindowGauge(
#         name="canary_unhealthy_1m",
#         documentation="Number of times the monitor was unhealthy in the last minute.",
#         labelnames=LABELS,
#         window=(60 * 1)
#     ),
#     EventWindowGauge(
#         name="canary_unhealthy_5m",
#         documentation="Number of times the monitor was unhealthy in the last 5 minutes.",
#         labelnames=LABELS,
#         window=(60 * 5)
#     ),
#     EventWindowGauge(
#         name="canary_unhealthy_1h",
#         documentation="Number of times the monitor was unhealthy in the last hour.",
#         labelnames=LABELS,
#         window=(60 * 60)
#     )
# ]
HEALTHY_LASTSEEN_GAUGE = Gauge(
    name="canary_healthy_lastseen",
    documentation="Timestamp of the most recent time a monitor was healthy.",
    labelnames=LABELS,
)
HEALTHY_EVENT_GAUGES = [
    EventWindowGauge(
        name="canary_healthy_1m",
        documentation="Number of times the monitor was healthy in the last minute.",
        labelnames=LABELS,
        window=(60 * 1)
    ),
    EventWindowGauge(
        name="canary_healthy_5m",
        documentation="Number of times the monitor was healthy in the last 5 minutes.",
        labelnames=LABELS,
        window=(60 * 5)
    ),
    EventWindowGauge(
        name="canary_healthy_1h",
        documentation="Number of times the monitor was healthy in the last hour.",
        labelnames=LABELS,
        window=(60 * 60)
    )
]


async def Monitor(name: str, spec: dict, labels: dict):
    """
    Monitors a given url at a regular interval and logs the result to prometheus.
    This co-routine loops forever unless it is externally cancelled, such as to recreate it with new settings..
    """

    # Hard clamp the interval to minimum of 5s to prevent DOS runaway
    # Still could be bad if running on a lot of nodes
    interval = max(MIN_MONITOR_INTERVAL, int(spec["interval"]))

    # Allow this to throw an exception if the url is invalid
    url = spec["url"]
    urllib.parse.urlparse(url)

    # TODO handle this as a list of valid statuses
    expected_status = str(spec["status"])

    # Add extra labels
    labels |= dict(monitor=name, url=url)

    header = f"[{name=}] [{interval=}] [{url=}]"
    logging.info(f"{header} | polling")

    try:
        while True:
            # Spawn a task to track the minimum amount of time to the next iteration and return immediately
            interval_task = asyncio.create_task(asyncio.sleep(interval))

            healthy = False
            try:
                # Poll the url
                timeout = aiohttp.ClientTimeout(total=interval)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, timeout=interval) as response:
                        status = str(response.status)

                # Check if the status code was acceptable
                healthy = status == expected_status
                logging.info(f"{header} | poll [{status=}] [{healthy=}]")

            except Exception as ex:
                logging.exception(f"{header} | poll error", exc_info=ex)

            # Update the unhealthy metric
            if healthy:
                HEALTHY_LASTSEEN_GAUGE.labels(**labels).set_to_current_time()
                for gauge in HEALTHY_EVENT_GAUGES:
                    gauge.update(labels=labels)
            # else:
            #     UNHEALTHY_LASTSEEN_GAUGE.labels(**labels).set_to_current_time()
            #     for gauge in UNHEALTHY_EVENT_GAUGES:
            #         gauge.update(labels=labels)

            # Update the status metric
            # STATUS_LASTSEEN_GAUGE.labels(**(labels | dict(status=status))).set_to_current_time()

            # Await the minimum interval, returns immediately if it's already passed
            await interval_task

    except asyncio.CancelledError:
        logging.info(f"{header} | cancelled")
    except Exception as ex:
        logging.error(f"{header} | error monitoring url", exc_info=ex)
    finally:
        logging.info(f"{header} | halting")
