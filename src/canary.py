import asyncio
import json

import aiohttp

import logging
import click
import kubernetes_asyncio.watch
from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient
from kubernetes_asyncio.client import Configuration

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
    # conf = Configuration()
    # conf.http_proxy_url = "http://192.168.10.15:8080"
    # await config.load_kube_config(client_configuration=conf)
    config.load_incluster_config()

    logging.info("starting watcher")
    logging.debug(args)
    logging.debug(kwargs)

    logging.info("listening for events")
    tasks = dict()
    runningTasks = dict()

    try:
        while True:
            logging.info("checking for updates on the cluster")
            async with ApiClient() as api:
                crds = client.CustomObjectsApi(api)
                rawmonitors = await crds.list_cluster_custom_object(group="canary.ukserp.ac.uk", version="v1",
                                                                    plural="canaryhttpmonitors")
                rawmonitors = rawmonitors["items"]
                monitor_names = []
                for monitor in rawmonitors:
                    name = monitor["metadata"]["name"]
                    monitor_names.append(name)
                    url = monitor["spec"]["url"]
                    interval = monitor["spec"]["interval"]
                    if type(monitor["spec"]["status"]) is not list:
                        statuses = []
                        statuses.append(monitor["spec"]["status"])
                    else:
                        statuses = monitor["spec"]["status"]

                    if name in tasks and (
                            runningTasks[name]['url'] != url or runningTasks[name]['interval'] != interval or runningTasks[name][
                        'statuses'] != statuses):
                        logging.info(f"cancelling monitor [{name=}]")
                        tasks[name].cancel()
                        runningTasks[name].popitem()
                        await tasks[name]
                        logging.info(f"spawning monitor [{name=}]")
                        runningTasks[name] = {'name': name, 'url': url, 'interval': interval, 'statuses': statuses}
                        tasks[name] = asyncio.create_task(
                            monitor_url(name, url, interval, statuses))

                    if name not in tasks:
                        logging.info(f"spawning monitor [{name=}]")
                        runningTasks[name] = {'name': name, 'url': url, 'interval': interval, 'statuses': statuses}
                        tasks[name] = asyncio.create_task(
                            monitor_url(name, url, interval, statuses))

                if len(rawmonitors) < len(tasks):
                    for task in runningTasks:
                        if task['name'] not in monitor_names:
                            logging.info(f"cancelling monitor [{name=}]")
                            tasks[task['name']].cancel()
                            runningTasks[task['name']].popitem()
            await asyncio.sleep(30)

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
