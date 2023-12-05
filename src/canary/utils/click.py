import click
import urllib.parse


class URL(click.ParamType):
    name = "url"

    def convert(self, value, param, ctx):
        if not isinstance(value, tuple):
            value = urllib.parse.urlparse(value)
            if value.scheme not in ("http", "https"):
                self.fail(
                    f"invalid URL scheme ({value.scheme}). Only HTTP URLs are allowed",
                    param,
                    ctx,
                )
        return value
