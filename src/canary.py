import logging
import click

from urllib.parse import urljoin

import asyncio
import aiohttp
import kubernetes_asyncio as k8s

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s %(filename)s:%(lineno)s %(funcName)s] %(message)s",
)


async def push_metric(url, job, metric):
    # http://prometheus-pushgateway.hiru-mgmt-monitoring.svc.cluster.local:9091
    put_url = urljoin(url, f"/metrics/job/{job}")

    async with aiohttp.ClientSession() as session:
        async with session.put(put_url, data=metric) as response:
            assert response.status == 200


async def monitor_url(name, spec):
    """
    Monitors a given url at a regular interval and logs the result to prometheus.
    This co-routine loops forever unless it is externally cancelled, such as to recreate it with new settings.
    """

    header = f"monitor | [name={name}] [interval={spec['interval']}] [url={spec['url']}]"
    try:
        while True:
            # Spawn a task to track the minimum amount of time to the next iteration and return immediately
            interval_task = asyncio.create_task(asyncio.sleep(spec["interval"]))

            try:
                # Poll the url
                async with aiohttp.ClientSession() as session:
                    async with session.get(spec["url"]) as response:
                        status = response.status

                # Check if the status code was acceptable
                healthy = status == spec["status"]

                logging.info(f"{header} | poll [{status=}] [{healthy=}]")

                # Write to Prometheus
                # TODO export metrics to prometheus

            except Exception as ex:
                logging.exception(f"{header} | ERROR", exc_info=ex)

                # Write to Prometheus
                # TODO export metrics to prometheus

            # Await the minimum interval, returns immediately if it's already passed
            await interval_task

    except asyncio.CancelledError:
        logging.info(f"{header} | cancelled")
    finally:
        logging.info(f"{header} | halting")


async def controller(*args, **kwargs):

    logging.info("controller | starting")
    logging.debug(f"controller | {args=}")
    logging.debug(f"controller | {kwargs=}")

    update_interval = kwargs["update_interval"]

    logging.info("controller | loading kube api config")
    k8s.config.load_incluster_config()

    monitors = dict()

    try:
        while True:

            logging.info("query kube api for monitors")
            async with k8s.client.CustomObjectsApi() as api:

                manifests = await api.list_cluster_custom_object(
                    group="canary.ukserp.ac.uk",
                    version="v1",
                    plural="canaryhttpmonitors"
                )

            # Convert the manifests into a dict keyed on namespace.name
            manifests = {
                f"{manifest['metadata']['namespace']}."
                f"{manifest['metadata']['name']}": manifest
                for manifest in manifests["items"]
            }
            logging.debug(f"discovered {len(manifests)} manifests")
            logging.debug(f"running {len(monitors)} monitors")

            # Cancel existing monitors that are not found in the live manifests
            for name, monitor in monitors.items():

                if name not in manifests:
                    logging.info(f"canceling monitor [{name=}]")
                    monitors[name]["task"].cancel()
                    # Don't care about waiting for this
                    # await monitors[name]["task"]
                    monitors.pop(name)

            # Create or re-create monitors to match the live manifests
            for name, manifest in manifests.items():

                if (name in monitors) and (monitors[name]["spec"] != manifest["spec"]):
                    logging.info(f"recreating monitor [{name=}]")
                    monitors[name]["task"].cancel()
                    await monitors[name]["task"]
                    monitors.pop(name)

                if name not in monitors:
                    logging.info(f"spawning monitor [{name=}]")
                    monitors[name] = dict(
                        name=name,
                        spec=manifest["spec"],
                        task=asyncio.create_task(
                            monitor_url(name=name, spec=manifest["spec"])
                        )
                    )

            # Pause before polling the kube api again
            await asyncio.sleep(update_interval)

    except asyncio.CancelledError:
        logging.info("cancelled")

    finally:
        logging.info("halting")

        for name, monitor in monitors.items():
            logging.info(f"canceling monitor [{name=}]")
            monitor["task"].cancel()

        await asyncio.gather(*map(lambda m: m["task"], monitors.values()))


@click.command()
@click.option(
    "-u",
    "--update-interval",
    type=click.IntRange(min=5, max_open=True),
    default=30,
    help="Update interval (seconds) for querying kubernetes api for monitor manifests.",
    show_default=True
)
def main(*args, **kwargs):
    logging.info("spawning controller")
    asyncio.run(controller(*args, **kwargs))
    logging.info("halting")


if __name__ == "__main__":
    main(auto_envvar_prefix='CANARY')
