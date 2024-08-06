import os
from collections.abc import Generator, Mapping
from pathlib import Path
from typing import Any, Literal, Optional, cast
from typing_extensions import Self

import msgspec
from msgspec import UNSET, UnsetType
from mergedeep import merge as deepmerge
from rich.console import Console
from rich.pretty import pprint


def make_dict(keys: list[str], value: Any) -> dict:
    result = nested = dict()  # type: dict[str, Any]
    for key in keys[:-1]:
        nested = nested.setdefault(key, {})
    nested[keys[-1]] = value
    return result


def parse_env(
    env: Mapping[str, Any],
    *,
    prefix: str,
) -> dict[str, Any | dict[str, Any]]:
    values: dict[str, Any] = dict()
    prefix = f"{prefix}_"
    N = len(prefix)
    for key, value in env.items():
        if not key.startswith(prefix):
            continue
        else:
            keys = list(map(str.lower, key[N:].split('.')))
            deepmerge(values, make_dict(keys, value))
    return values


class Struct(msgspec.Struct):
    """A `Struct` which also behaves like a `Mapping`"""

    def __iter__(self) -> Generator[tuple[str, Any], None, None]:
        for field in self.__struct_fields__:
            value = getattr(self, field)
            if value is not UNSET:
                yield (field, value)

    def __getitem__(self, field):
        attr = getattr(self, field)
        if isinstance(attr, Struct):
            return msgspec.to_builtins(attr)
        else:
            return attr

    def keys(self):
        return self.__struct_fields__


class ConfigBase(Struct, kw_only=True, frozen=True):

    @classmethod
    def from_file(cls, *, path: Path | str) -> Self:
        path = Path(path).expanduser().absolute()
        return msgspec.json.decode(path.read_bytes(), type=cls)

    @classmethod
    def from_env(cls, *, prefix: str) -> Self:
        kwargs = parse_env(os.environ, prefix=prefix)
        return msgspec.convert(kwargs, cls, strict=False)

    def update(self, *, merge: bool = True, **fields) -> Self:
        cls = type(self)
        kwargs: dict[str, Any] = dict(self)
        if merge:
            deepmerge(kwargs, fields)
        else:
            kwargs.update(fields)
        return msgspec.convert(kwargs, cls, strict=False)

    def update_env(self, *, prefix: str, merge: bool = True) -> Self:
        cls = type(self)
        kwargs: dict[str, Any] = dict(self)
        fields: dict[str, Any] = parse_env(os.environ, prefix=prefix)
        if merge:
            deepmerge(kwargs, fields)
        else:
            kwargs.update(fields)
        return msgspec.convert(kwargs, cls, strict=False)

    def __repr__(self) -> str:
        console = Console(
            width=88, markup=False, highlight=False, no_color=True
        )
        with console.capture() as capture:
            console.print(self)
        return capture.get()

    def _ipython_display_(self):
        pprint(self, indent_guides=False)
