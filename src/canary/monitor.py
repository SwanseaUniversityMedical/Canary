import logging
import datetime
import asyncio
import aiohttp
import urllib.parse

from .pushgateway import push_metrics

MIN_MONITOR_INTERVAL = 5  # seconds


async def Monitor(name: str, spec: dict, pushgateway: dict):
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

    header = f"[{name=}] [{interval=}] [{url=}]"
    logging.info(f"{header} | polling")

    try:
        while True:
            # Spawn a task to track the minimum amount of time to the next iteration and return immediately
            interval_task = asyncio.create_task(asyncio.sleep(interval))

            metrics = dict()

            try:
                # Poll the url
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        status = str(response.status)

                # Check if the status code was acceptable
                healthy = status == expected_status

                logging.info(f"{header} | poll [{status=}] [{healthy=}]")

                metrics |= dict(
                    healthy=(1 if healthy else 0),
                    status=status
                )

            except Exception as ex:
                logging.exception(f"{header} | ERROR", exc_info=ex)

                metrics |= dict(error=1)

            await push_metrics(
                **pushgateway,
                labels=dict(
                    timestamp=datetime.datetime.now().timestamp(),
                    monitor=name,
                    url=spec["url"]
                ),
                metrics=metrics
            )

            # Await the minimum interval, returns immediately if it's already passed
            await interval_task

    except asyncio.CancelledError:
        logging.info(f"{header} | cancelled")
    finally:
        logging.info(f"{header} | halting")
