# Sprint 5: release readiness

Scope: release the core and functional plugins without preserving the superseded schema behavior.
Use Dockerfile for Linux validation, as requested; WSL was inspected but not used for testing.

No PyPI publication or external issue creation is authorized by this sprint.

Release candidates: core 0.8.0, issue-tracker 0.4.0, chat 0.2.0, universal 0.2.0.
Assess GitHub-sync and SQLite-export scaffolds separately; do not claim their placeholder behavior
is production-ready. The core SQLite snapshot index does not make the export stub functional.

Gates:
- Normalize user-facing errors for configuration, paths, encodings, and storage failures.
- Resolve plugin schema/entry-point/provenance incompatibilities; test functional plugin behavior.
- Build wheels and sdists and inspect archive contents/metadata.
- Install each candidate artifact with only declared dependencies outside the checkout; smoke core
  APIs and CLI, both schemas, mutations/index refresh, and plugin discovery and reporting.
- Run core interpreter matrix on Windows and artifact/core/plugin tests on Docker Desktop Linux containers.
- Configure macOS/Linux/Windows artifact tests in CI; report any platform not executed here honestly.
- Publish only artifacts built from the exact tagged revision after passing release tests. Never
  mutate version/changelog files on a different revision after creating the release tag.
- Record concise Unreleased changelog entries, candidate artifacts, checks, and remaining limits.


Identity correction from the owner's shared-ticket observation: all independently managed source tags
receive local IDs, including tracker-linked tags. Local ID takes precedence in source identity;
tracker links remain shareable, and parent issues remain separate. Old skip behavior is removed.

## Validation results

Validated on 2026-09-10:
- Windows Python 3.9–3.15: 471 core tests passed, 5 skipped, on every interpreter; coverage about 86%.
  Python 3.15 was a release candidate, not a final release.
- Windows Python 3.9–3.15: 93 functional plugin tests passed, 2 skipped, on every interpreter.
- Docker Desktop Linux Python 3.9.25 and 3.14.7: core and plugin suites passed, together with
  isolated wheel and source-archive installs and API/CLI smoke checks.
- Windows Python 3.14.6: all four wheels and all four source archives installed successfully in
  clean runtime-only environments; strict Twine metadata checks passed.
- Formatting, import ordering, pre-commit checks, and whitespace validation passed.

Candidates are in `.build/release-candidates/`, grouped by project, with hashes in `SHA256SUMS.json`.
The core archive excludes plugin directories and installs without the development workspace.
The smoke checks cover explicit schemas, mutation/index refresh, clean CLI errors, plugin discovery,
issue reports and HTML templates, and universal source collection.

The functional candidates are ready for the release CI gate. macOS is configured in CI but was not
executed locally. No remote workflow, tag, commit, or PyPI publication was performed in this sprint.
Before publication, finalize the release changelog and committed versions, run the tagged CI gates,
and configure the package's PyPI trusted publisher. Publish core before its dependent plugins.

GitHub-sync and SQLite-export remain held at 0.1.0 because their implementations are scaffolds.
The universal plugin supports standalone JavaScript/TypeScript line comments and remains read-only;
the core mutation and SQLite index APIs operate on Python source. Chat provides a discussion schema,
not a messaging service. Full index refresh still reads selected source bytes; repeated snapshot
lookups use SQLite indexes. These boundaries are intentional and documented.

## Release automation update

The release flow now follows the kacl-m release-branch/PR process used by bash2yaml.
The earlier requirement to bump all version files before creating a GitHub release is
superseded for the core. Checks run on the prepared commit SHA and publication uses those
exact tested artifacts. See [publishing the core](../docs/releasing.md).
