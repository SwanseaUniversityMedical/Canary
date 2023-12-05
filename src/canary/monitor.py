import logging
import asyncio
import aiohttp
import urllib.parse
from prometheus_client import Gauge

MIN_MONITOR_INTERVAL = 5  # seconds


async def Monitor(name: str, spec: dict, labels: dict):
    """
    Monitors a given url at a regular interval and logs the result to prometheus.
    This co-routine loops forever unless it is externally cancelled, such as to recreate it with new settings.
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

    # Gauges for different status codes
    status_lastseen_gauge = Gauge(
        name="canary_status_lastseen",
        documentation="Timestamp of the most recent time a status code was observed.",
        labelnames=list(labels.keys()) + ["status"],
    )
    unhealthy_lastseen_gauge = Gauge(
        name="canary_unhealthy_lastseen",
        documentation="Timestamp of the most recent time a monitor was unhealthy.",
        labelnames=list(labels.keys()),
    )

    header = f"[{name=}] [{interval=}] [{url=}]"
    logging.info(f"{header} | polling")

    try:
        while True:
            # Spawn a task to track the minimum amount of time to the next iteration and return immediately
            interval_task = asyncio.create_task(asyncio.sleep(interval))

            try:
                # Poll the url
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        status = str(response.status)

                # Check if the status code was acceptable
                healthy = status == expected_status

                # Update the unhealthy metric
                if not healthy:
                    unhealthy_lastseen_gauge.labels(**labels).set_to_current_time()

                logging.info(f"{header} | poll [{status=}] [{healthy=}]")

                # Update the status metric
                status_lastseen_gauge.labels(**(labels | dict(status=status))).set_to_current_time()

            except Exception as ex:
                logging.exception(f"{header} | ERROR", exc_info=ex)

                # Update the unhealthy metric
                unhealthy_lastseen_gauge.labels(**labels).set_to_current_time()

            # Await the minimum interval, returns immediately if it's already passed
            await interval_task

    except asyncio.CancelledError:
        logging.info(f"{header} | cancelled")
    except Exception as ex:
        logging.error(f"{header} | error monitoring url", exc_info=ex)
    finally:
        logging.info(f"{header} | halting")
