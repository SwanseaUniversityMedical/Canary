import logging
import urllib.parse
import aiohttp


def format_metrics(timestamp: float, metrics: dict, labels: dict):

    def format_label(kv):
        label, value = kv
        return f"{label}=\"{value}\""

    # timestamp = f"{int(float(timestamp) * 1000):d}"
    # labels |= dict(timestamp=timestamp)
    labels_str = ", ".join(map(format_label, labels.items()))

    def format_metric(kv):
        metric, value = kv
        return f"""
        # TYPE canary_{metric} gauge
        canary_{metric}{{{labels_str}}} {value}
        """.strip()

    return "\n".join(map(format_metric, metrics.items()))


async def push_metrics(url: str, job: str, instance: str, extra_labels: dict, timestamp: float, labels: dict, metrics: dict):
    # Construct url to submit the metrics to
    metric_path = (
        f"/metrics/job/{urllib.parse.quote_plus(job)}"
        f"/instance/{urllib.parse.quote_plus(instance)}"
    )

    url = urllib.parse.urlparse(url)
    url = urllib.parse.urlunparse((url.scheme, url.netloc, url.path, "", "", ""))
    url = urllib.parse.urljoin(url, metric_path)
    logging.debug(f"pushing metrics [{url=}]")

    logging.debug(f"{extra_labels=}")
    logging.debug(f"{labels=}")
    logging.debug(f"{metrics=}")

    labels = extra_labels | labels
    logging.debug(f"{labels=}")

    data = format_metrics(timestamp=timestamp, labels=labels, metrics=metrics)

    # Temporary debug of metrics output
    for line in data.split("\n"):
        logging.debug(f"metrics | {line}")

    try:
        # Submit the metrics to the pushgateway
        async with aiohttp.ClientSession() as session:
            async with session.put(url, data=data) as response:
                assert response.status == 200

    except Exception as ex:
        logging.error("error pushing metrics to gateway", exc_info=ex)
