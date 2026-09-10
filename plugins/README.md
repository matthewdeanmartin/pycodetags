# Release readiness for core 0.8.0

| Package | Candidate | Decision |
| --- | --- | --- |
| pycodetags-issue-tracker | 0.4.0 | Rebuild: schema, identity/provenance, reporting fixes |
| pycodetags-chat | 0.2.0 | Rebuild: entry point, explicit discussion schema, metadata |
| pycodetags-universal | 0.2.0 | Rebuild: explicit TDG/PEP-350 standalone line comments |
| pycodetags-github-issues-sync | existing 0.1.0 | Hold: placeholder synchronization and obsolete hook names |
| pycodetags-to-sqlite | existing 0.1.0 | Hold: export hooks have no implementation |

The three candidates require core 0.8.x and Python 3.9–3.15. No compatibility layer for the previous
implicit schema behavior is supplied. The held packages are not release candidates; do not install
them as part of the supported bundle. Core TagIndex supplies the working SQLite snapshot capability.
No real GitHub synchronization is claimed or attempted by this release.

# These are plugin examples.

These are not distributed and exist only as example code and to exercise plugin functionality.

## pycodetags_chat
Developers chat in source code. 

Feature road map
- The tool extract discussions to a browsable website.
- Remove comments from resolved or stale chats. 
- Filter to unanswered questions.
- Message users when replies appear in source code.

## pycodetags_issue_tracker
Generic issue tracker.

Feature road map
- Extract various reports or websites
- Remove comments of closed issues
- Hooks to sync with external trackers
- Identity system and hooks
- Stop on overdue
- Decorators and Context Managers as "TODOs"
- NotImplemented, Deprecated as TODOs

## pycodetags_universal
If a file type isn't python, the file path is fed to this plugin.

Illustrates finding a code tag in a file type that isn't python.