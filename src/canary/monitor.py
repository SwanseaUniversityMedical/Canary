import logging
import asyncio
import time

import aiohttp
import urllib.parse
from prometheus_client import Gauge

MIN_MONITOR_INTERVAL = 5  # seconds

LABELS = [
    "node",
    "pod",
    "namespace",
    "release",
    "monitor",
]

REQUEST_DURATION_GAUGE = Gauge(
    name="canary_request_duration",
    documentation="Duration of poll event in seconds.",
    labelnames=LABELS,
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
STATUS_LASTSEEN_GAUGE = Gauge(
    name="canary_status_lastseen",
    documentation="Timestamp of the most recent time a monitor showed a status code.",
    labelnames=LABELS+["status"],
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

    expected_status = str(spec["status"])

    # If this monitor specifies its own proxy setting
    if spec["proxy"] is not None:
        if spec["proxy"]["url"] is None:
            # If the monitor specifies a null url we explicitly disable using a proxy
            proxy = None
        else:
            # Otherwise we replace the global proxy setting passed to canary with the
            # one the monitor specifies
            proxy = spec["proxy"]["url"]

    # Add extra labels
    labels = labels | dict(monitor=name)

    # Normalize label order to ensure we can remove labels later
    labels = {key: labels[key] for key in LABELS}

    header = f"[{name=}] [{interval=}] [{url=}] [{proxy=}]"
    logging.info(f"{header} | polling")

    # A set to keep track of unique status codes we've seen so that
    # we can clean up the metrics when this monitor is halted
    observed_status = set()

    try:
        while True:
            # Spawn a task to track the minimum amount of time to the next iteration and return immediately
            interval_task = asyncio.create_task(asyncio.sleep(interval))

            start_time = time.time()
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

                # Update per status code metric
                observed_status.add(status)
                STATUS_LASTSEEN_GAUGE.labels(**(labels | dict(status=status))).set(time.time() * 1000.)

            except Exception as ex:
                logging.exception(f"{header} | poll error", exc_info=ex)

            end_time = time.time()
            REQUEST_DURATION_GAUGE.labels(**labels).set(max(0., end_time - start_time))

            # Update the unhealthy metric
            if healthy:
                HEALTHY_GAUGE.labels(**labels).set(1)
                HEALTHY_LASTSEEN_GAUGE.labels(**labels).set(time.time() * 1000.)

            else:
                HEALTHY_GAUGE.labels(**labels).set(0)
                UNHEALTHY_LASTSEEN_GAUGE.labels(**labels).set(time.time() * 1000.)

            # Await the minimum interval, returns immediately if it's already passed
            await interval_task

    except asyncio.CancelledError:
        logging.info(f"{header} | cancelled")
    except Exception as ex:
        logging.error(f"{header} | error monitoring url", exc_info=ex)
    finally:
        logging.info(f"{header} | halting")

        try:
            logging.debug(f"{header} | removing metric canary_request_duration {labels=}")
            REQUEST_DURATION_GAUGE.remove(*labels.values())
        except KeyError:
            pass
        
        try:
            logging.debug(f"{header} | removing metric canary_healthy {labels=}")
            HEALTHY_GAUGE.remove(*labels.values())
        except KeyError:
            pass

        try:
            logging.debug(f"{header} | removing metric canary_healthy_lastseen {labels=}")
            HEALTHY_LASTSEEN_GAUGE.remove(*labels.values())
        except KeyError:
            pass

        try:
            logging.debug(f"{header} | removing metric canary_unhealthy_lastseen {labels=}")
            UNHEALTHY_LASTSEEN_GAUGE.remove(*labels.values())
        except KeyError:
            pass

        for status in observed_status:
            try:
                logging.debug(f"{header} | removing metric canary_status_lastseen {labels=}")
                STATUS_LASTSEEN_GAUGE.remove(*(labels | dict(status=status)).values())
            except KeyError:
                pass
