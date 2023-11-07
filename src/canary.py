import asyncio
import aiohttp

import random
import logging
import click
from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient


logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s %(filename)s:%(lineno)s %(funcName)s] %(message)s",
)


async def monitor_url(name, url, interval, statuses):
    """
    Monitors a given url at a regular interval and logs the result to prometheus.
    This co-routine loops forever unless it is externally cancelled, such as to recreate it with new settings.
    """

    logging.info(f"starting [{name=}]")
    try:
        while True:
            logging.debug(f"polling [{name=}] [{interval=}] [{url=}]")

            # Spawn a task to track the minimum amount of time to the next iteration and return immediately
            interval_task = asyncio.create_task(asyncio.sleep(interval))

            try:
                # Poll the url
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        status = response.status

                # Check if the status code was acceptible
                healthy = status in statuses
                logging.info(
                    f"polled [{name=}] [{interval=}] [{url=}] [{status=}] [{healthy=}]"
                )

                # Write to Prometheus
                # TODO export metrics to prometheus

            except Exception as ex:
                logging.exception(f"poll error [{name=}]", exc_info=ex)

            # Await the minimum interval, returns immediately if it's already passed
            await interval_task

    except asyncio.CancelledError:
        logging.info(f"cancelled [{name=}]")
    finally:
        logging.info(f"halting [{name=}]")


async def watch_events(*args, **kwargs):
    config.load_incluster_config()

    logging.info("starting watcher")
    logging.debug(args)
    logging.debug(kwargs)
    monitors = [
        {
            "name": "airflow",
            "url": "https://airflow.sail-teleport.dk.serp.ac.uk",
            "interval": 10,
            "expect": {"status": [200]},
        },
        {
            "name": "rabbitmq",
            "url": "https://rabbitmq.sail-teleport.dk.serp.ac.uk",
            "interval": 10,
            "expect": {"status": [200]},
        },
    ]

    logging.info("listening for events")
    tasks = dict()

    try:
        # Created monitors for current objects
        # TODO Query kubes for existing CanaryHTTPMonitor objects that are visible and iterate over them
        # use the context manager to close http sessions automatically
        async with ApiClient() as api:
            crds = client.CustomObjectsApi(api)
            rawmonitors = await crds.list_cluster_custom_object(group="canary.ukserp.ac.uk", version="v1", plural="canaryhttpmonitors")
            rawmonitors = rawmonitors["items"]
            for monitor in rawmonitors:
                name = monitor["metadata"]["name"]
                url = monitor["spec"]["url"]
                interval = monitor["spec"]["interval"]
                statuses = monitor["spec"]["status"]
                print(name + " " + url + " " + str(interval) + " " + str(statuses))
            print(monitors)
            exit(0)
            for monitor in monitors:
                # Get monitor (simulated)
                name = monitor["name"]
                url = monitor["url"]
                statuses = monitor["expect"]["status"]
                interval = monitor["interval"] + random.randint(0, 10)
                logging.info(f"spawning monitor [{name=}]")
                tasks[name] = asyncio.create_task(
                    monitor_url(name, url, interval, statuses)
                )

        # Consume events
        # TODO Subscript to kubes event queue for changes to CanaryHTTPMonitor objects that are visible
        while True:
            # Get event (simulated)
            await asyncio.sleep(30)
            monitor = random.choice(monitors)
            name = monitor["name"]
            url = monitor["url"]
            statuses = monitor["expect"]["status"]
            interval = monitor["interval"] + random.randint(0, 10)
            event = "UPDATED"

            # Cancel the task if it already exists
            if name in tasks:
                logging.info(f"cancelling monitor [{name=}]")
                tasks[name].cancel()
                await tasks[name]

            # Create a new task at the desired interval
            if event in ["ADDED", "UPDATED"]:
                logging.info(f"spawning monitor [{name=}]")
                tasks[name] = asyncio.create_task(
                    monitor_url(name, url, interval, statuses)
                )

    except asyncio.CancelledError:
        logging.info("cancelled watcher")
        for task in tasks.values():
            task.cancel()

        await asyncio.gather(*tasks.values())
    finally:
        logging.info("halting watcher")


@click.command()
def main(*args, **kwargs):
    asyncio.run(watch_events(*args, **kwargs))


if __name__ == "__main__":
    main()
