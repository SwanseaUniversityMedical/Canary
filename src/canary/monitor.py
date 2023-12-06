import logging
import asyncio
import time

import aiohttp
import urllib.parse

from .metrics import MetricServer

MIN_MONITOR_INTERVAL = 5  # seconds

LABELS = [
    "k8s_node_name",
    "k8s_pod_name",
    "k8s_pod_namespace",
    "monitor",
    "url"
]


async def Monitor(name: str, spec: dict, labels: dict, metric_server: MetricServer):
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
    labels = labels | dict(monitor=name, url=url)

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
                    async with session.get(url, timeout=interval, proxy="http://192.168.10.15:8080") as response:
                        status = str(response.status)

                # Check if the status code was acceptable
                healthy = status == expected_status
                logging.info(f"{header} | poll [{status=}] [{healthy=}]")

            except Exception as ex:
                logging.exception(f"{header} | poll error", exc_info=ex)

            # Update the unhealthy metric
            if healthy:
                await metric_server.add(metric="canary_healthy_lastseen", labels=labels, value=time.time())
            else:
                await metric_server.add(metric="canary_unhealthy_lastseen", labels=labels, value=time.time())

            # Update the status metric
            await metric_server.add(metric="canary_status_lastseen", labels=(labels | dict(status=status)), value=time.time())

            # Await the minimum interval, returns immediately if it's already passed
            await interval_task

    except asyncio.CancelledError:
        logging.info(f"{header} | cancelled")
    except Exception as ex:
        logging.error(f"{header} | error monitoring url", exc_info=ex)
    finally:
        logging.info(f"{header} | halting")
