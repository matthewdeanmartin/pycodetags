# pycodetags

You've seen `# TODO:` comments? What if they could be used as an issue tracker?

What if `# TODO:` style comments could serialize and deserialize records, turning comments into a database?

What if you could also write comments as decorators that warn or stop you on the due date?

Replace or complement your `# TODO:` comments with decorators similar to NotImplement, Deprecated or Warning
and get issue tracker features, too.

Lightweight and keeps your issue tracker in your code.

Backwards compatible with both `# TODO:` comments and PEP-350 comments.

## Note on Name

Package name is `pycodetags`. The obvious package name is taken and anything with dash or underscore is ungoogleable. Sorry.



## Prior Art

PEPs and Standard Library Prior Art

- [PEP 350 - Code Tags](https://peps.python.org/pep-0350/) Rejected proposal
- [NotImplementedException](https://docs.python.org/3/library/exceptions.html#NotImplementedError) is a blunt way to stop code at an undone point
- `pass` does the same, but doesn't care if you haven't gotten around to it. Linters might make you get
  rid of pass if you've added a docstring, making pass syntactically unnecessary.
- print/logging/warning is noiser way to show undone tasks.
- [DeprecationWarning](https://docs.python.org/3/library/exceptions.html#DeprecationWarning) Deprecation shows a future code removal task.

Community Python Tools

- [todo](https://pypi.org/project/todo/) Extract and print TODOs in code base
- [geoffrey-todo](https://pypi.org/project/geoffrey-todo/) Same.
- [flake8-todo](https://pypi.org/project/flake8-todo/) Yell at you if you leave TODO in the source. Pylint also does this.
- pytest's skip test is a type of TODO
- [xfail](https://pypi.org/project/xfail/) - Same, but as a plugin
- [deprecation](https://pypi.org/project/deprecation/) Deprecation attribute

See [PRIOR_ART.md](docs_wip/PRIOR_ART.md) for survey of the whole ecosystem.

