# Installation

## Comments-only, Zero Dependencies

You don't install anything into your application, add code tags to your source code, nothing ships with your
application. Compatible with all versions of python that have ever existed.

To get the reports, validation, etc, install pycodetags globally either standalone...

```bash
pipx install pycodetags
```

... or with plugins

```bash
pipx install pycodetags pypcodetags-issue-tracker
```

To later add more plugins, use the inject keyword in `pipx`

```bash
pipx inject pycodetags pypcodetags-issue-tracker
```

## Advanced. Live TODOs with behaviors

For code tag decorators, objects, exceptions, context managers with run-time behavior:

```bash
pip install pycodetags
```

Requires python 3.8+, but 3.7 will probably work.

The only dependencies are `pluggy` and `ast-comments` and `jmespath` and backports of python standard libraries to support old versions
of python.
