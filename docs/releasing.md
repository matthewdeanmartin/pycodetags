# Releasing packages

Releases use kacl-m 6.9.0 or later. Each component owns the changelog, version files,
and tag template listed in the root `pyproject.toml`.

| Package | kacl-m component | Tag example |
| --- | --- | --- |
| pycodetags | default | v0.8.2 |
| pycodetags-issue-tracker | pycodetags-issue-tracker | pycodetags-issue-tracker-v0.4.0 |

The examples illustrate tag spelling, not a decision about the next version.
Chat and universal plugins are tested but are not enabled for publishing.

## Draft and publish

1. Add release notes to the selected component's `[Unreleased]` section.
2. Run **Create Draft Release** in Actions and select the component. Optionally set
   a version; otherwise kacl-m infers it from that changelog. Pushes to main update
   the core draft only. Review the version and notes before publishing the draft.
3. Publishing the GitHub release starts **Release**. kacl-m bumps only the selected
   component's files and opens a release PR. One Linux build tests the prepared
   commit, then publishes only that component's artifacts to PyPI.
4. Merge the release PR after publication succeeds.

For a local preview, with `GITHUB_TOKEN` set:

```shell
uv run --frozen kaclm --component pycodetags-issue-tracker --json github-release --repository matthewdeanmartin/pycodetags --dry-run
uv run --frozen kaclm --component pycodetags-issue-tracker --json release-bump --version pycodetags-issue-tracker-v0.4.0 --dry-run --yes
```

`make draft-release COMPONENT=pycodetags-issue-tracker REPOSITORY=owner/repo` also
selects the plugin. Omitting `COMPONENT` selects the core.

Both packages must authorize `release.yml` as their PyPI Trusted Publisher, using
this repository and the `pypi` environment. Replace any issue tracker publisher
configured for `publish_issue_tracker_plugin.yml`; that separate workflow is retired.
The workflow needs repository permission to create pull requests.

Version bumps do not rewrite sibling versions, dependency constraints, or the shared
`uv.lock`. The artifact checks install the core and plugins together and will fail if
an intended core release no longer satisfies a plugin's dependency constraint. Resolve
that compatibility decision before publishing. When dependencies change, regenerate
and commit `uv.lock` as usual.

Review the inferred version against published releases when changelog history is
incomplete; use the explicit draft version when necessary.

## Existing failed runs

Re-running a historical Actions run uses its old workflow. After updating the default
branch, start the current workflow explicitly for an existing GitHub release:

```shell
gh workflow run release.yml --ref main -f release_tag=pycodetags-issue-tracker-v0.4.0
```

This starts publication. Use an existing release whose package version has not already
been published. The GitHub tag requests the version; artifacts come from kacl-m's
prepared commit. The workflow does not move the original tag.
