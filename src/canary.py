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
@click.option(
    "--k8s-release-name",
    type=str,
    required=True,
    help="Name of the helm release.",
    show_default=True
)
@click.option(
    "--proxy",
    type=URL(),
    default=None,
    help="URL to a HTTP proxy sever to use by default.",
    show_default=True
)
def main(*args, **kwargs):
    logging.info("spawning controller")
    asyncio.run(Controller(*args, **kwargs))
    logging.info("halting")


if __name__ == "__main__":
    main(auto_envvar_prefix='CANARY')
