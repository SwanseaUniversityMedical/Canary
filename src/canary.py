import asyncio
import aiohttp

import logging
import click
import kubernetes_asyncio.watch
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

    logging.info("listening for events")
    tasks = dict()

    try:
        # Create monitors for current objects
        async with ApiClient() as api:
            crds = client.CustomObjectsApi(api)
            rawmonitors = await crds.list_cluster_custom_object(group="canary.ukserp.ac.uk", version="v1", plural="canaryhttpmonitors")
            rawmonitors = rawmonitors["items"]
            for monitor in rawmonitors:
                name = monitor["metadata"]["name"]
                url = monitor["spec"]["url"]
                interval = monitor["spec"]["interval"]
                if type(monitor["spec"]["status"]) is not list:
                    statuses = []
                    statuses.append(monitor["spec"]["status"])
                else:
                    statuses = monitor["spec"]["status"]
                tasks[name] = asyncio.create_task(
                    monitor_url(name, url, interval, statuses)
                )

        # Consume events
        # TODO Subscript to kubes event queue for changes to CanaryHTTPMonitor objects that are visible
        watch = kubernetes_asyncio.watch.Watch()

        namespace = "canary"

        async with watch.stream(crds.list_namespaced_custom_object, "canary.ukserp.ac.uk", "v1", namespace, "canaryhttpmonitors") as stream:
            async for event in stream:
                print(event)
                name = monitor["metadata"]["name"]
                url = monitor["spec"]["url"]
                interval = monitor["spec"]["interval"]
                statuses = monitor["spec"]["status"]

                # Cancel the task if it already exists or was deleted
                if name in tasks or event["type"] == "DELETED":
                    logging.info(f"cancelling monitor [{name=}]")
                    watch.stop()
                    tasks[name].cancel()
                    await tasks[name]

                # Create a new task
                if event["type"] in ["ADDED", "MODIFIED"]:
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
