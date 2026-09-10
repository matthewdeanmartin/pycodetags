# Publishing the core

kacl-m owns version selection, version-file updates, changelog releases, and release PRs.
The draft-release workflow asks kacl-m to propose a release from `[Unreleased]`.
Publishing the GitHub release starts `release.yml`:

1. Check out the repository's default branch.
2. Run `kaclm --json release-bump --open-pr` for the requested version.
3. Build and test the resulting commit on Linux with Python 3.14.
4. Publish the tested core wheel and source archive after the `pypi` environment approval.
5. Merge kacl-m's release PR after publication succeeds.

There is no local version-preparation script or tag-versus-metadata gate. The remaining
artifact helper only builds packages and tests installs. Package metadata validation and
runtime tests remain in place; they do not select or rewrite release versions.

The GitHub release tag requests the version. Builds use kacl-m's prepared commit, and the
workflow does not move the original tag. CI has one Linux job and no platform or Python-version
matrix. GitHub Actions must be allowed to create PRs; PyPI must trust `release.yml` and `pypi`.

## Existing failed runs

Re-running a historical release run uses its old workflow, including any old matrix or tag checks.
After updating the default branch, start the current workflow explicitly for an existing release:

```shell
gh workflow run release.yml --ref main -f release_tag=v0.8.1
```

This starts publication, so use it only after release-tool issues are resolved and the package
version has not already been published. The referenced GitHub release must exist.

## kacl-m limitations

The installed kacl-m 6.8.0 can change nested plugin version constants during a core release.
It also does not refresh the shared uv lockfile as part of release preparation. These belong
in kacl-m, not in pycodetags-specific version scripts. The reproducible bug and proposed
component support are recorded in [kacl-m monorepo support](../spec/kaclm_monorepo.md).
Resolve that upstream before using automated core releases in this monorepo.

The plugin publisher uploads only the explicitly selected plugin's artifacts. It does not
use a pycodetags-specific tag/version naming gate; prepare the intended plugin metadata with
the release tooling before selecting its source tag.
