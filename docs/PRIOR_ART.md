# Prior Art - Code Tags

## Code Tags and PEP 350

- [PEP 350 - Code Tags](https://peps.python.org/pep-0350/)
- [Blog post about code tags](https://canadiancoding.ca/CodeTags%20in%20Python)

## Folk Tags

### Parenthesis with anonymous Defalts
[Chromiums Coding Standards](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/ios/style.md#todo-comments)
e.g. `// TODO(crbug.com/######): Something that needs doing.`

[Google C++ Coding Standards](https://google.github.io/styleguide/cppguide.html#TODO_Comments)
e.g. 
```cpp
// TODO: bug 12345678 - Remove this after the 2047q4 compatibility window expires.
// TODO: example.com/my-design-doc - Manually fix up this code the next time it's touched.
// TODO(bug 12345678): Update this list after the Foo service is turned down.
// TODO(John): Use a "\*" here for concatenation operator.
```

[Khan Java](https://github.com/Khan/style-guides/blob/master/style/java.md#use-todo-comments-with-author-name)
e.g.
```java
// TODO(author): ...
```

Example where issue follows `:` and before a `-`
[Diktat](https://github.com/saveourtool/diktat/blob/master/info/guide/diktat-coding-convention.md#243-code-delivered-to-the-client-should-not-contain-todofixme-comments)
```java
// TODO(<author-name>): Jira-XXX - support new json format
// FIXME: Jira-XXX - fix NPE in this code block
```

[TDG Style Extensions](https://github.com/marketplace/actions/track-todo-action#todo-comments)
```c
// TODO: This is title of the issue to create
// category=SomeCategory issue=123 estimate=30m author=alias
// This is a multiline description of the issue
// that will be in the "Body" property of the comment
```


## Tools to Compile and print TODOs

- [todo](https://pypi.org/project/todo/) Extract and print TODOs in code base
- [tdg](https://gitlab.com/ribtoks/tdg) Same.
- [geoffrey-todo](https://pypi.org/project/geoffrey-todo/) Same.
- [todo.md](https://github.com/todo-md/todo-md) Suggestion for a TODO.md standard
- [leosot](https://github.com/pgilad/leasot) Javascript library to support TODO-extraction for multiple languages

## Integration Tools

- [track-todo-action](https://github.com/marketplace/actions/track-todo-action) Syncs TODO in source code to github actions
- [todocheck](https://github.com/presmihaylov/todocheck) Validates that all TODO have valid tracker ID as looked up in jira, etc.
- [smart_todo](https://github.com/Shopify/smart_todo) Sends message when it finds TODOs that match criteria (e.g. due date)

## Linters

- [flake8-todo](https://pypi.org/project/flake8-todo/) Yell at you if you leave TODO in the source. Pylint also does this.

- [phpstan-todo-by](https://github.com/staabm/phpstan-todo-by) TODO's become an error after due date.

Linters, especially if run frequently, are the opposite to my goal. I want TODOs in my source code, not
to stomp them out. Besides, linters don't make you do the work, they just make you stop indicating what
is a TODO comment with a marker. You can still write a ton of TODOs without bothering the linter because
linters aren't that kind of smart.

## Standards

- [Java's code tags (@TODO in javadoc)](https://web.archive.org/web/20111001031644/http://java.sun.com/j2se/javadoc/proposed-tags.html)
- [PEP 350](https://peps.python.org/pep-0350/) - Code Tags

## IDE Support

- [Clion](https://www.jetbrains.com/help/clion/using-todo.html) All Jebrains IDEs support some sort of TODO list summarization.

Jetbrains products can treat the second line of a code tag as a continuation if it is indented.
