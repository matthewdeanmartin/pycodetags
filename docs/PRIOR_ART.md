# Prior Art

## Code Tags and PEP 350

- [PEP 350 - Code Tags](https://peps.python.org/pep-0350/)
- [Blog post about code tags](https://canadiancoding.ca/CodeTags%20in%20Python)

## Tools to Compile and print TODOs

- [todo](https://pypi.org/project/todo/) Extract and print TODOs in code base
- [geoffrey-todo](https://pypi.org/project/geoffrey-todo/) Same.
- [todo.md](https://github.com/todo-md/todo-md) Suggestion for a TODO.md standard
- [leosot](https://github.com/pgilad/leasot) Javascript library to support TODO-extraction for multiple languages

## Integration Tools

- [todocheck](https://github.com/presmihaylov/todocheck) Validates that all TODO have valid tracker ID as looked up in jira, etc.
- [smart_todo](https://github.com/Shopify/smart_todo) Sends message when it finds TODOs that match criteria (e.g. due date)

## Linters

- [flake8-todo](https://pypi.org/project/flake8-todo/) Yell at you if you leave TODO in the source. Pylint also does this.

- [phpstan-todo-by](https://github.com/staabm/phpstan-todo-by) TODO's become an error after due date.

Linters, especially if run frequently, are the opposite to my goal. I want TODOs in my source code, not
to stomp them out. Besides, linters don't make you do the work, they just make you stop indicating what
is a TODO comment with a marker. You can still write a ton of TODOs without bothering the linter because
linters aren't that kind of smart.

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

## Standards

- [Java's code tags (@TODO in javadoc)](https://web.archive.org/web/20111001031644/http://java.sun.com/j2se/javadoc/proposed-tags.html)
- [PEP 350](https://peps.python.org/pep-0350/) - Code Tags

## IDE Support

- [Clion](https://www.jetbrains.com/help/clion/using-todo.html) All Jebrains IDEs support some sort of TODO list summarization.

Jetbrains products can treat the second line of a code tag as a continuation if it is indented.
