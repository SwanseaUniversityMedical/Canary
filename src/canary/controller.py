import logging
import asyncio
import kubernetes_asyncio as k8s
from prometheus_async.aio.web import start_http_server

from .monitor import Monitor


async def Controller(*args, **kwargs):

    logging.info("controller | starting")
    logging.debug(f"controller | {args=}")
    logging.debug(f"controller | {kwargs=}")

    update_interval = kwargs["k8s_update_interval"]
    labels = dict(
        k8s_node_name=kwargs["k8s_node_name"],
        k8s_pod_name=kwargs["k8s_pod_name"],
        k8s_pod_namespace=kwargs["k8s_pod_namespace"]
    )

    logging.info("controller | loading kube api config")
    k8s.config.load_incluster_config()

    monitors = dict()

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
                    await monitors[name]["task"]
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

                    # Spawn a coroutine task
                    task = asyncio.create_task(
                        Monitor(
                            name=name,
                            spec=manifest["spec"],
                            labels=labels
                        )
                    )

                    # Keep track of the task and the spec that it was spawned from
                    monitors[name] = dict(
                        name=name,
                        spec=manifest["spec"],
                        task=task
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
