import logging
import click
import asyncio

from canary.utils.click import URL
from canary.controller import Controller

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s %(filename)s:%(lineno)s %(funcName)s] %(message)s",
)


@click.command()
@click.option(
    "--metric-url",
    type=URL(),
    required=True,
    help="URL to a prometheus pushgateway.",
    show_default=True
)
@click.option(
    "--metric-job",
    type=str,
    required=True,
    help="Prometheus job name for metrics.",
    show_default=True
)
@click.option(
    "--metric-instance",
    type=str,
    required=True,
    help="Prometheus instance name for metrics.",
    show_default=True
)
@click.option(
    "--k8s-update-interval",
    type=click.IntRange(min=5, max_open=True),
    default=30,
    help="Update interval (seconds) for querying kubernetes api for monitor manifests.",
    show_default=True
)
@click.option(
    "--k8s-node-name",
    type=str,
    required=True,
    help="Name of the node running the controller pod.",
    show_default=True
)
@click.option(
    "--k8s-pod-name",
    type=str,
    required=True,
    help="Name of the controller pod.",
    show_default=True
)
@click.option(
    "--k8s-pod-namespace",
    type=str,
    required=True,
    help="Namespace where the controller is running.",
    show_default=True
)
def main(*args, **kwargs):
    logging.info("spawning controller")
    asyncio.run(Controller(*args, **kwargs))
    logging.info("halting")


if __name__ == "__main__":
    main(auto_envvar_prefix='CANARY')
