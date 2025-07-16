# PYCODETAGS PEP 004 — Catdogs

| PEP:             | 004                                                                               |
|------------------|-----------------------------------------------------------------------------------|
| Title:           | Catdogs – Unified List/Scalar Hybrid Types                                        |
| Author:          | Matthew Martin [matthewdeanmartin@gmail.com](mailto\:matthewdeanmartin@gmail.com) |
| Author:          | ChatGPT (gpt-4-turbo, OpenAI)                                                     |
| Status:          | Draft                                                                             |
| Type:            | Standards Track                                                                   |
| Created:         | 2025-07-12                                                                        |
| License:         | MIT                                                                               |
| Intended Version | ≥ 0.7.0                                                                           |

## Abstract

This PEP introduces the `Catdog` family of types: hybrid scalar-list objects that allow seamless support for
`str | list[str]`, `int | list[int]`, and `float | list[float]` fields in data tags. These hybrid types conform to PEP
350’s design while avoiding lossy behavior.

---

## Motivation

PEP 350 defines code tags where fields may be written as:

```python
# TODO: Implement caching <assignee:alice>
# TODO: Implement caching <assignee:alice,bob>
```

In the first case, `assignee` is a scalar string. In the second, it’s a list. However, internally treating these as
`str | list[str]` leads to:

* Complicated downstream code (`isinstance(x, str)`, `if not isinstance(x, list)`, etc.)
* Risk of *lossy conversion* when simplifying to string
* Inconsistent semantics across fields

To solve this, we introduce the **Catdog** — a list-backed type that behaves like both a list and a scalar, *without
discarding data*.

---

## Goals

* Support `str | list[str]`, `int | list[int]`, `float | list[float]` through well-behaved types
* Never lose underlying values (no conversion that discards data)
* Provide clean APIs for developers (e.g. `.as_scalar()` or `.as_list()`)

---

## Specification

### 1. `CatdogStr`: `str | list[str]`

```python
from pycodetags.catdogs import CatdogStr

x = CatdogStr("alice")
y = CatdogStr(["alice", "bob"])

assert str(x) == "alice"
assert str(y) == "alice,bob"
assert y[1] == "bob"
assert len(y) == 2
assert y.as_list() == ["alice", "bob"]
assert y.as_scalar() == "alice,bob"
```

### 2. `CatdogInt`: `int | list[int]`

```python
z = CatdogInt([1, 2, 3])
assert z[0] == 1
assert sum(z) == 6
assert z.as_scalar() == "1,2,3"
assert z.as_list() == [1, 2, 3]
```

### 3. `CatdogFloat`: `float | list[float]`

Same semantics as `CatdogInt`, but for floats.

---

## Behavior Matrix

| Operation         | Returns / Affects  | Notes                                 |
|-------------------|--------------------|---------------------------------------|
| `__getitem__`     | Item from list     | List-like                             |
| `__str__`         | Comma-joined str   | Non-lossy                             |
| `__len__`         | List length        |                                       |
| `__eq__`          | List equality      | Works with raw list or another Catdog |
| `.as_list()`      | `list[T]`          | Never mutates                         |
| `.as_scalar()`    | `str`              | Returns comma-joined string           |
| `.append(x)`      | Mutates list       | Optional                              |
| `.first()`        | Returns first item | Shortcut for `[0]`                    |
| `.is_scalarish()` | Bool               | True if one item                      |

---

## Implementation Sketch

```python
class CatdogBase:
    def __init__(self, value: str | list[str]):
        self._items = [value] if isinstance(value, str) else list(value)

    def __getitem__(self, i):
        return self._items[i]

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __eq__(self, other):
        return self._items == (other._items if isinstance(other, CatdogBase) else other)

    def as_list(self):
        return self._items.copy()

    def as_scalar(self):
        return ",".join(str(x) for x in self._items)

    def __str__(self):
        return self.as_scalar()

    def first(self):
        return self._items[0] if self._items else None

    def is_scalarish(self):
        return len(self._items) <= 1
```

Then:

```python
class CatdogStr(CatdogBase): ...


class CatdogInt(CatdogBase): ...


class CatdogFloat(CatdogBase): ...
```

Each subclass enforces type constraints on contents.

---

## Integration Plan

* [ ] Add `catdogs.py` to `pycodetags/`
* [ ] Support in `parse_fields()` and `promote_fields()` for auto-wrapping
* [ ] Add support to `to_flat_dict()` and `.to_dict()` serialization
* [ ] Add tests to `tests/test_catdogs.py`
* [ ] Enable optional toggling of Catdog wrapping in config or constructor

---

## Open Questions

* Should `CatdogStr("a,b")` parse to `["a", "b"]` or preserve `"a,b"` as a single item?
    * **Proposed**: Always explicit — split only on `<...>` parsing, not during instantiation.
* Should JSON serialization output list or scalar?
    * **Proposed**: Always list in JSON for predictability.

---

## Benefits

* Clean, predictable handling of mixed scalar/list fields
* Avoids loss or ambiguity in value representation
* Promotes best practices around flexible schemas (esp. user-assigned fields)

---

## Alternatives Considered

* Using `Union[str, list[str]]` directly

    * Verbose and unsafe downstream
* Always treating as list

    * Breaks compatibility with PEP350-style single-line fields
* External libraries like `pydantic`'s smart coercion

    * Violates PyCodeTags’ **pure Python** philosophy

---

## Summary

The Catdog types enable clean, lossless support for scalar-or-list fields without complicating downstream logic or
requiring external tools. These hybrid types are both developer-friendly and conformant with the spirit of PEP 350.

## Reference Impementation

```python

# pycodetags/catdogs.py

from __future__ import annotations
from typing import Iterator, Union, TypeVar, Generic, overload, Any

T = TypeVar("T", str, int, float)


class CatdogBase(Generic[T]):
    def __init__(self, value: Union[T, list[T]]) -> None:
        if isinstance(value, list):
            self._items: list[T] = list(value)
        else:
            self._items = [value]

    def __getitem__(self, index: int) -> T:
        return self._items[index]

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, CatdogBase):
            return self._items == other._items
        if isinstance(other, list):
            return self._items == other
        return False

    def __str__(self) -> str:
        return self.as_scalar()

    def __repr__(self) -> str:
        type_name = self.__class__.__name__
        return f"{type_name}({self._items!r})"

    def append(self, item: T) -> None:
        self._items.append(item)

    def extend(self, values: list[T]) -> None:
        self._items.extend(values)

    def first(self) -> T | None:
        return self._items[0] if self._items else None

    def as_list(self) -> list[T]:
        return self._items.copy()

    def is_scalarish(self) -> bool:
        return len(self._items) <= 1

    def as_scalar(self) -> str:
        return ",".join(str(x) for x in self._items)


class CatdogStr(CatdogBase[str]):
    def __init__(self, value: str | list[str]) -> None:
        if isinstance(value, list):
            if not all(isinstance(x, str) for x in value):
                raise TypeError("CatdogStr expects only str or list[str]")
        elif not isinstance(value, str):
            raise TypeError("CatdogStr expects str or list[str]")
        super().__init__(value)


class CatdogInt(CatdogBase[int]):
    def __init__(self, value: int | list[int]) -> None:
        if isinstance(value, list):
            if not all(isinstance(x, int) for x in value):
                raise TypeError("CatdogInt expects only int or list[int]")
        elif not isinstance(value, int):
            raise TypeError("CatdogInt expects int or list[int]")
        super().__init__(value)

    def __sum__(self) -> int:
        return sum(self._items)


class CatdogFloat(CatdogBase[float]):
    def __init__(self, value: float | list[float]) -> None:
        if isinstance(value, list):
            if not all(isinstance(x, (float, int)) for x in value):
                raise TypeError("CatdogFloat expects only float or list[float]")
            value = [float(x) for x in value]
        elif isinstance(value, (float, int)):
            value = float(value)
        else:
            raise TypeError("CatdogFloat expects float or list[float]")
        super().__init__(value)

    def __sum__(self) -> float:
        return sum(self._items)


```

## Copyright

This document is licensed under the MIT License.
