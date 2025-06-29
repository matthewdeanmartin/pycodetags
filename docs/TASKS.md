# TODO

## REFACTOR TO DOMAIN NEUTRAL TAGS
- Including a strongly domain specific "app" like an issue tracker will sink data tags as a 3rd party library
- chat, issue tracker, code review, documentation must be plugins
  - each domain specific plugin app has 1 schema
  - other plugins can additional functionality and filter for the schema they recognize.
- Per schema plugins add functionality
  - For cli commands
  - Reports (filtered by schema)
  - Validation (filtered by schema)
- TODO exceptions are a problem. Like Warning, Deprecation, NotImplemented, they don't implement the same properties
  - Remove for now. - DONE

## Basic Types Issues
- Identity, strict, fuzzy, by schema
  - Need this for tracking issues across git history.
- Overlapping values and strict mode
  - See promotion code, which lacks a good unit test.
- Huge mess with assignee/assignees being both `str | list[str]` Should probably force to always be list[str]: STILL A MESS
  - Maybe implement S() type that is a wrapper of str and list[str] with reasonable interface
- Need to check if roundtripping is possible

## Tracker/Config
- Need
  - domain to detect if URL is tracker URL
  - ticket to allow short form
  - link format to put domain and ticket into a full url, e.g. http://{domain}/ticket?id={tracker} (security risks?)

## 350 Parser
- Merging default and alias not implemented yet (e.g. <priority:3 p:2> or <Jack assignee:John a:Jill>): MOSTLY DONE.
- assignee value is a mini csv format, delegate to python eval? csv parser?

## Folk Tags
- Person/Assignee needs to be list[str] and support CSV serialization for parallelism with 350 parser: MESSY
- Finds tags inside of doc strings! Those aren't comments!

## CLI conveniences
- Turn off folk tags, turn off PEP tags individually. Can do by config, not by CLI
- Infer location of source code, `pycodetags report .`

## Public Interface
- Put basic things in CORE
- put everything else in another noncore library (otherwise plugins must import things not in the `__all__` export)

## Other big things
- TRICKY: Need identity code, Add Identity logic (% identical and configurable threshold)- PARTIAL
- BIG: Probably need AST version of TODO() finder because crawling the object graph of a module is missing a lot.
- Use keepachangelog for versions/releases (Future releases/unreleased is biggest holdup)
- Use release schema for display/sorting
- per-project config file in pyproject.toml (maybe remove dynaconfig)
- add pytest-like plugin support
- Basic dashboard
- BIG: Need git integration (as plugin?)
- Basic git integration
  - find code tags that have since been deleted
  - fill in origination/start/finish dates based on git dates
- basic localization - PARTIAL(via config)

## Plugin handler
- Do anything with a file found in folder (right now, plugin gets file only if build-in search skips it) : Done?

## Other issues

Ironically, the library isn't ready to track its own TODO

- TODOFixTest: implement it!
- Some sort of GIT integration
- Write to file. Piping to stdout is picking up too much cruft. - Partial implmentation?

## Web Dashboard

- Report by responsible user (stand up report)
- Report by version/iteration/release (road map)
- Done (changelog)
- Report by tag (e.g. "bug", "feature", "enhancement")
- Metrics: time to close, overdue

## Converters

- Add meta fields (file, line, original text, original schema)

## Views

- switch more to jina2

## Config (TODO)

- Workflow params
  - Action is log/print
- User Identification
  - Get user by github - Out of scope?
  - Get user by .env - need .env file support in general.

# Integrations

- Plugins. No heavy integrations. BASICALLY DONE!
- Create issues in tracker via API (needs plugin!) EXAMPLE AVAIL!
- Two way issue tracker sync (needs plugin!) EXAMPLE AVAIL!

# Precommit

- Out of scope- "Delete all TODOs before commit". If people don't want code tags, they also won't use this library.
- don't commit if due, if due for active user

# Build steps/Release steps

- Generate HTML representations
- Generate standard docs
  - TODO.md - Kind of done, clunky, not sure if it works with kanban plugin.
  - DONE.md - DONE
  - CHANGELOG.md - Need to validate.
- Before release pipx install and exercise it!

## Git Integration

- Search history for completed issues (deleted TODO)
- add standard file revision field

## User Names

- AUTHORS.md driven - Partially done
- Git driven- Integration! Maybe needs plugin?

