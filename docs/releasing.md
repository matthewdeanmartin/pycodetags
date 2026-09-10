# Publishing the core

The draft-release workflow uses kacl-m to propose the next release from `[Unreleased]`.
Publishing that GitHub release starts `release.yml`:

1. Check out the repository's default branch.
2. Prepare the core's `pyproject.toml`, `pycodetags/__about__.py`, and `uv.lock` for the release version.
3. Run `kaclm --json release-bump --pyproject-only --open-pr` to release the changelog,
   commit the prepared files, push `codex/release-v<version>`, and open the release PR.
4. Run the shared compatibility and artifact checks against the resulting commit SHA.
5. Publish only the tested core wheel and source archive after the `pypi` environment approval.
6. Merge the release PR after publication succeeds so the default branch reflects the release.

This follows the bash2yaml release flow. The GitHub release tag is the version request;
the package is built from the prepared release-branch commit, which contains the version bump.
The workflow does not move the original tag. Subsequent changes to the branch cannot change
which commit the checks use. All three operating systems test artifacts; only the Ubuntu
artifacts are uploaded to PyPI.

GitHub Actions must be allowed to create pull requests, and PyPI must trust `release.yml`
with the `pypi` environment. The workflow does not merge the release PR automatically.

## Retry an existing release

Once the updated workflow is on the default branch, a failed release such as `v0.8.1`
can be prepared and published using that workflow:

```shell
gh workflow run release.yml --ref main -f release_tag=v0.8.1
```

Use the repository's default branch if it is not `main`. The GitHub release must already
exist. This starts publication; use it for a release whose package upload has not succeeded.
Re-running an old failed workflow does not load newer workflow definitions.

## Independent plugin releases

Core releases do not bump or publish plugin versions. The existing plugin workflow still
requires a plugin tag matching its committed metadata. Automatic plugin release PRs are a
separate step; see the [kacl-m monorepo proposal](../spec/kaclm_monorepo.md).

The preparation helper deliberately names the two core version files. kacl-m's current
recursive Python version discovery is not scoped to a component, so the core release uses
`--pyproject-only` after explicitly preparing `__about__.py`. Its commit also includes the
tracked lockfile changes. This workaround can be removed when kacl-m supports explicit
component version targets and lockfile updates.
