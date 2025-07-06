"""
Code Tag TODOs.
"""

#
# # TODO
#
# ## TOP PRIORITIES
# - `pycodetags issues init` command to setup config.
#   - DONE (for data).
#   - Need for Issues

# TODO: `pycodetags issues fill-in-defaults` command to speed up data entry <matth 2025-07-06 category=cli
#  priority=high>

# TODO:  Need concept of default value for recognized fields. The copy paste and clutter cost is too high now.

# TODO: Need to be able to edit, maybe restrict to code blocks with one `<>` and only edit those fields

# TODO: Folk tag need help: Need offsets for locating Folk Tags in source code. Needs testing <matth 2025-07-06 category=parsing
#  priority=high status=done iteration=1>

# TODO: Need offsets for second, third tags within a comment block.<matth 2025-07-06 category=cli
#   priority=high status=development iteration=1>

# TODO: Move all issues into python source (EASY) <matth 2025-07-06 category=build priority=high status=development iteration=1>

# TODO: Add validate to build (make check) <matth 2025-07-06 category=build priority=high status=development iteration=1>

# TODO: Add Generate issue_site and publish with gha <matth 2025-07-06 category=build priority=high status=development iteration=1>

# TODO: Add Generate changelog <matth 2025-07-06 category=build priority=high status=development iteration=1>

# TODO: Before release pipx install and exercise it! <matth 2025-07-06 category=build priority=high status=development iteration=1>

# TODO: Add Identity feature (HARD) Enables git features (find originator, find origination date, find close date)
# <matth 2025-07-06 category=base priority=high status=development iteration=1>

# TODO: Revisit "Todo Objects" Raise an TODOException, e.g. `raise TODOException("Work on this")`
#   <matth 2025-07-06 category=core priority=low status=development iteration=1>

# TODO: Add a TODOSkipTest decorator <matth 2025-07-06 category=core priority=low status=development iteration=1>

# TODO: assignee value is a mini csv format, delegate to python eval? csv parser? <matth 2025-07-06 category=core priority=medium status=development iteration=1>

# TODO: Create a python list of TODO() objects.  <matth 2025-07-06 category=core priority=low status=development iteration=1>


# ## REFACTOR TO DOMAIN NEUTRAL TAGS
# - chat, issue tracker, code review, documentation must be plugins
#   - each domain specific plugin app has 1 schema
#   - other plugins can additional functionality and filter for the schema they recognize.
# - Per schema plugins add functionality
#   - For cli commands
#   - Reports (filtered by schema)
#   - Validation (filtered by schema)
# - TODO exceptions are a problem. Like Warning, Deprecation, NotImplemented, they don't implement the same properties
#
# ## Basic Types Issues
# - Identity, strict, fuzzy, by schema
#   - Need this for tracking issues across git history.
# - Overlapping values and strict mode
#   - See promotion code, which lacks a good unit test.
# - Huge mess with assignee/assignees being both `str | list[str]` Should probably force to always be list[str]: STILL A MESS
#   - Maybe implement S() type that is a wrapper of str and list[str] with reasonable interface
#
# ## Tracker/Config
# - Need
#   - domain to detect if URL is tracker URL
#   - ticket to allow short form
#   - link format to put domain and ticket into a full url, e.g. http://{domain}/ticket?id={tracker} (security risks?)

# ## Folk Tags
# - Person/Assignee needs to be list[str] and support CSV serialization for parallelism with 350 parser: MESSY
# - Finds tags inside of doc strings! Those aren't comments!
#
# ## CLI conveniences
# - Turn off folk tags, turn off PEP tags individually. Can do by config, not by CLI
# - Infer location of source code, `pycodetags report .`
#
# ## Public Interface
# - Put basic things in CORE
# - put everything else in another noncore library (otherwise plugins must import things not in the `__all__` export)
#
# ## Other big things
# - TRICKY: Need identity code, Add Identity logic (% identical and configurable threshold)- PARTIAL

# TODO: Object TODOs. Probably need AST version of TODO() finder because crawling the object graph of a module is missing a lot.

# TODO: future releases for keepachangelog for versions/releases (Future releases/unreleased is biggest holdup)
# TODO: Use changelog release schema for display/sorting

# - BIG: Need git integration (as plugin?)
# - Basic git integration
#   - find code tags that have since been deleted
#   - fill in origination/start/finish dates based on git dates
# - basic localization - PARTIAL(via config)
#
# ## Plugin handler
# - Do anything with a file found in folder (right now, plugin gets file only if build-in search skips it) : Done?
#
# ## Other issues
#
# Ironically, the library isn't ready to track its own TODO
#
# TODO: TODOFixTest: implement it!
# TODO: Some sort of GIT integration
# TODO: Write to file. Piping to stdout is picking up too much cruft. - Partial implmentation?


# TODO: Report by responsible user (stand up report)
# TODO: Report by version/iteration/release (road map)
# TODO: Done (changelog)
# TODO: Report by tag (e.g. "bug", "feature", "enhancement")
# TODO: Metrics: time to close, overdue

# TODO: validate that everything with a file has meta fields (file, line, original text, original schema)<matth 2025-07-06 status=development category=core priority=high release=1.0.0 iteration=1>
# TODO: views switch more to jina2 <matth 2025-07-06 status=development category=core priority=high release=1.0.0 iteration=1>

# WONTDO: Out of scope- "Delete all TODOs before commit". If people don't want code tags, they also won't use this library. <matth 2025-07-06 status=development category=core priority=high release=1.0.0 iteration=1>
# TODO: precommit - don't commit if due, if due for active user <matth 2025-07-06 status=development category=core priority=high release=1.0.0 iteration=1>

# TODO: TODO.md - Kind of done, clunky, not sure if it works with kanban plugin. <matth 2025-07-06 status=development category=core priority=high release=1.0.0 iteration=1>
# TODO: improve DONE.md <matth 2025-07-06 status=development category=core priority=high release=1.0.0 iteration=1>
# TODO: unit test CHANGELOG.md - Need to validate. <matth 2025-07-06 status=development category=core priority=high release=1.0.0 iteration=1>

# TODO: Git Integration - Search history for completed issues (deleted TODO) <matth 2025-07-06 status=development category=core priority=high release=1.0.0 iteration=1>
# TODO: Git Integration -  add standard file revision field <matth 2025-07-06 status=development category=core priority=high release=1.0.0 iteration=1>

# TODO: User Names AUTHORS.md driven - Partially done <matth 2025-07-06 status=development category=core priority=high release=1.0.0 iteration=1>
# TODO: Git driven- Integration! Maybe needs plugin? <matth 2025-07-06 status=development category=core priority=high release=1.0.0 iteration=1>
