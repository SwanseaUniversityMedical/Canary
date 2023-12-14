import logging
import asyncio
# import glob
# import os
# import yaml

import kubernetes_asyncio as k8s
from prometheus_async.aio.web import start_http_server
from prometheus_client import Gauge

from .monitor import Monitor


async def controller(*args, **kwargs):

    logging.info("controller | starting")
    logging.debug(f"controller | {args=}")
    logging.debug(f"controller | {kwargs=}")

    update_interval = kwargs["k8s_update_interval"]
    proxy = kwargs["proxy"]
    labels = dict(
        node=kwargs["k8s_node_name"],
        pod=kwargs["k8s_pod_name"],
        namespace=kwargs["k8s_pod_namespace"],
        release=kwargs["k8s_release_name"]
    )

    logging.info("controller | loading kube api config")
    k8s.config.load_incluster_config()

    monitors = dict()

    MONITORS_GAUGE = Gauge(
        name="canary_monitors",
        documentation="Number of monitors being tracked by a canary controller.",
        labelnames=list(labels.keys())
    )

    try:
        await start_http_server(port=8080)

        while True:

            logging.info("query kube api for monitors")
            async with k8s.client.ApiClient() as api:
                crds = k8s.client.CustomObjectsApi(api)
                manifests = await crds.list_cluster_custom_object(
                    group="canary.ukserp.ac.uk",
                    version="v1",
                    plural="canaryhttpmonitors"
                )

            # manifest_path = os.path.join(
            #     os.path.dirname(__file__),
            #     "../../charts/canary/templates/monitors/*.yaml"
            # )
            # manifest_paths = list(
            #     glob.glob(
            #         manifest_path
            #     )
            # )
            # manifests = dict(items=list())
            # for manifest_path in manifest_paths:
            #     with open(manifest_path, "r") as fp:
            #         manifest = yaml.safe_load(fp)
            #         manifests["items"].append(manifest)
            #         logging.info(manifest)

            # Convert the manifests into a dict keyed on namespace.name
            manifests = {
                f"{manifest['metadata']['namespace']}."
                f"{manifest['metadata']['name']}": manifest
                for manifest in manifests["items"]
            }
            logging.debug(f"discovered {len(manifests)} manifests")
            logging.debug(f"running {len(monitors)} monitors")

            # Cancel existing monitors that are not found in the live manifests
            for name in list(monitors.keys()):

                if name not in manifests:
                    logging.info(f"canceling monitor [{name=}]")
                    try:
                        monitors[name]["task"].cancel()
                        await monitors[name]["task"]
                    finally:
                        del monitors[name]

            # Create or re-create monitors to match the live manifests
            for name, manifest in manifests.items():

                if (name in monitors) and (monitors[name]["spec"] != manifest["spec"]):
                    logging.info(f"recreating monitor [{name=}]")
                    try:
                        monitors[name]["task"].cancel()
                        await monitors[name]["task"]
                    finally:
                        del monitors[name]

                if name not in monitors:
                    logging.info(f"spawning monitor [{name=}]")

                    # Spawn a coroutine task
                    task = asyncio.create_task(
                        Monitor(
                            name=name,
                            spec=manifest["spec"],
                            labels=labels,
                            proxy=proxy
                        )
                    )

                    # Keep track of the task and the spec that it was spawned from
                    monitors[name] = dict(
                        name=name,
                        spec=manifest["spec"],
                        task=task
                    )

            # Update the metric for how many monitors we are running
            MONITORS_GAUGE.labels(**labels).set(len(monitors))

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

Controller = controller
