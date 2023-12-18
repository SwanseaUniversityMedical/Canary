import click
import urllib.parse


class URL(click.ParamType):
    name = "url"

    def convert(self, value, param, ctx):
        if not isinstance(value, tuple):
            parsed = urllib.parse.urlparse(value)
            if parsed.scheme not in ("http", "https"):
                self.fail(
                    f"invalid URL scheme ({parsed.scheme}) for url ({value}). Only HTTP URLs are allowed",
                    param,
                    ctx,
                )
        return value
