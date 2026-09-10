# kacl-m monorepo release support

Status: proposal, not implemented. Based on the installed kacl-m 6.8.0 and the local
keepachangelog-manager source inspected during the pycodetags release workflow update.

## Current boundary

Components select changelogs, and matching paths can assign changes to components.
That is useful for monorepo change collection, but it does not define a package release.
The release service calls the version bumper without a component-specific project root.
The bumper operates from the working directory and discovers Python version files recursively.
`release-bump` stages the root `pyproject.toml` and all tracked modifications with `git add -u`.
Its default branch naming is based on the release ID or version, not the selected component.

The local development version improves ignored-directory handling and offers a version-file
plan. Those improvements do not establish independent package boundaries: tracked plugin
version files are still legitimate discovery candidates.

## First useful increment

Extend each component with explicit release targets. Suggested fields below are new API,
not configuration supported by the current tool:

```toml
[[tool.changelogmanager.components]]
name = "core"
changelog = "CHANGELOG.md"
project_root = "."
version_files = ["pyproject.toml", "pycodetags/__about__.py"]
tag_template = "v{version}"

[[tool.changelogmanager.components]]
name = "issue-tracker"
changelog = "plugins/pycodetags_issue_tracker/CHANGELOG.md"
project_root = "plugins/pycodetags_issue_tracker"
version_files = ["pyproject.toml", "pycodetags_issue_tracker/__about__.py"]
tag_template = "pycodetags-issue-tracker-v{version}"
```

Define changelog paths relative to the repository root, and version-file paths relative
to `project_root`. Resolve and validate paths before modifying files. In explicit mode,
only listed targets may change; avoid recursive discovery. Reject overlapping ownership
unless a file is explicitly declared shared. Include the component in generated branch names.

`--component issue-tracker release-bump` should carry that selection through version
calculation, changelog release, version updates, tag parsing, branch naming, and PR creation.
A core release must leave all plugin versions untouched, even when packages share a commit.

## Shared workspace files

Provide an explicit preparation phase before committing, allowing a workspace lock refresh
such as `uv lock`. Require declared shared outputs (here `uv.lock`), and inspect the resulting
changed-file set. Stage only the selected component's targets and declared shared outputs;
refuse unrelated edits rather than including every tracked change with `git add -u`.
Configuration commands execute only when explicitly requested by the release operation;
a dry-run must not execute them.

## Release plan and outputs

Use one release plan for draft creation, preparation, and validation, so these operations
agree on the selected component, next version, and tag. JSON should expose the component,
version, tag, branch, resulting commit SHA, changed files, and PR URL. GitHub Actions can
then check out the exact commit without independently reconstructing names or versions.

Test a fixture containing a core and two plugins with independent versions. Verify each
component release changes only its targets and declared shared files, uses the matching tag,
and produces a repeatable preview. Cover two components at the same version, an existing
release branch on retry, unrelated dirty files, and a failed lock refresh before any commit.

Start with explicit version-file scoping and JSON outputs. Dependency-range propagation,
coordinated multi-package releases, and automatic tag movement can remain separate decisions.
