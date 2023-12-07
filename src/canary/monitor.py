import logging
import asyncio
import aiohttp
import urllib.parse
from prometheus_client import Gauge

MIN_MONITOR_INTERVAL = 5  # seconds

LABELS = (
    "k8s_node_name",
    "k8s_pod_name",
    "k8s_pod_namespace",
    "monitor",
)

HEALTHY_GAUGE = Gauge(
    name="canary_healthy",
    documentation="Health of the last poll for a url as a boolean 0 (unhealthy) or 1 (healthy).",
    labelnames=LABELS,
)
HEALTHY_LASTSEEN_GAUGE = Gauge(
    name="canary_healthy_lastseen",
    documentation="Timestamp of the most recent time a monitor was healthy.",
    labelnames=LABELS,
)
UNHEALTHY_LASTSEEN_GAUGE = Gauge(
    name="canary_unhealthy_lastseen",
    documentation="Timestamp of the most recent time a monitor was unhealthy.",
    labelnames=LABELS,
)


async def Monitor(name: str, spec: dict, labels: dict, proxy: str):
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
    labels = labels | dict(monitor=name)

    # Normalize label order to ensure we can remove labels later
    labels = {key: labels[key] for key in LABELS}

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
                    async with session.get(url, timeout=interval, proxy=proxy) as response:
                        status = str(response.status)

                # Check if the status code was acceptable
                healthy = status == expected_status
                logging.info(f"{header} | poll [{status=}] [{healthy=}]")

            except Exception as ex:
                logging.exception(f"{header} | poll error", exc_info=ex)

            # Update the unhealthy metric
            if healthy:
                HEALTHY_GAUGE.labels(**labels).set(1)
                HEALTHY_LASTSEEN_GAUGE.labels(**labels).set_to_current_time()

            else:
                HEALTHY_GAUGE.labels(**labels).set(0)
                UNHEALTHY_LASTSEEN_GAUGE.labels(**labels).set_to_current_time()

            # Await the minimum interval, returns immediately if it's already passed
            await interval_task

    except asyncio.CancelledError:
        logging.info(f"{header} | cancelled")
    except Exception as ex:
        logging.error(f"{header} | error monitoring url", exc_info=ex)
    finally:
        logging.info(f"{header} | halting")

        try:
            HEALTHY_GAUGE.remove(*labels.values())
        except KeyError as ex:
            pass

        try:
            HEALTHY_LASTSEEN_GAUGE.remove(*labels.values())
        except KeyError as ex:
            pass

        try:
            UNHEALTHY_LASTSEEN_GAUGE.remove(*labels.values())
        except KeyError as ex:
            pass