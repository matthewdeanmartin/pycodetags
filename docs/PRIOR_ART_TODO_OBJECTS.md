# Prior Art - TODO Objects

## What are TODO Objects?

Anything that indicates a task needs to be done. NotImplementedError(), but also the objects in the pycodetags library
that have a similar structure to an evaluated comment code tag.

- NotImplementedException  - a promise to implement it
- Deprecations - a promise to remove this code
- Feature Flags - a promise to finish this feature
- Skip Test - a promise to fix or remove this test
- TODO() - a pycodetags DataTag object with runtime behavior- to stop or log when it is due or meets other criteria

## Tests

- pytest's skip test is a type of TODO
- [xfail](https://pypi.org/project/xfail/) - Same, but as a plugin

The existing skip test mechanisms are fine, but they don't integrate with the rest of source code TODO patterns.

## NotImplemented/pass

- [NotImplementedException](https://docs.python.org/3/library/exceptions.html#NotImplementedError) is a blunt way to
  stop code with pending work from running. It includes a place to put your TODO text as an exception message.
- `pass` does the same, but doesn't care if you haven't gotten around to it. Linters might make you get
  rid of pass if you've added a docstring, making pass syntactically unnecessary.
- print/logging/warning is noiser way to show

## Deprecation

Represents work todo- code that needs to be removed by some version or release.

- [deprecation](https://pypi.org/project/deprecation/) Deprecation attribute
- [DeprecationWarning](https://docs.python.org/3/library/exceptions.html#DeprecationWarning)

## Feature Flags

- [django-waffle](https://pypi.org/project/django-waffle/) Free, but django-centric.
- [unleash-client](https://pypi.org/project/unleash-client/) Paid, but very fancy and very cool.

Feature flags are a TODO in the sense of work that is *in progress* and you know you're not done.
