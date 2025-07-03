## Installation

For code tags strictly in comments:

`pipx install pycodetags`

For code tag decorators, objects, exceptions, context managers with run-time behavior:

`pip install pycodetags`

Requires python 3.8+. 3.7 will probably work.

The only dependencies are `pluggy` and `ast-comments` and backports of python standard libraries to support old versions
of python. For pure-comment style code tags, pipx install and nothing is installed with your application code.

