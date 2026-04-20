# Rulesets

GitHub rulesets committed as JSON so branch and tag protection policies live
under version control instead of scattered in the web UI.

## Apply with `gh` CLI

```bash
# Replace OWNER/REPO with your org/user + repo name.
OWNER_REPO="SciKMS/scikms"

gh api -X POST "/repos/${OWNER_REPO}/rulesets" \
  --input .github/rulesets/main-branch-protection.json

gh api -X POST "/repos/${OWNER_REPO}/rulesets" \
  --input .github/rulesets/release-tag-protection.json
```

To update an existing ruleset (after editing the JSON):

```bash
# List first to find the ruleset ID
gh api "/repos/${OWNER_REPO}/rulesets" | jq '.[] | {id, name}'

# Then PUT the update
gh api -X PUT "/repos/${OWNER_REPO}/rulesets/<RULESET_ID>" \
  --input .github/rulesets/main-branch-protection.json
```

## What each ruleset does

### `main-branch-protection.json`

Applied to the repo default branch (`main`).

- **Block deletion** — can't accidentally `git push origin :main`
- **Block force push** — no rewriting history of main
- **Require linear history** — merge commits rejected; use squash or rebase
- **Require PR with 1 approval** — no direct commits; stale approvals dismissed on new push
- **Require conversation resolution** — all PR comments must be resolved before merge
- **Require status checks** — the 4 test jobs from [`build.yml`](../workflows/build.yml) must pass:
  - `Test · ubuntu-latest · Python 3.10`
  - `Test · ubuntu-latest · Python 3.12`
  - `Test · macos-latest · Python 3.12`
  - `Test · windows-latest · Python 3.12`
- **Allowed merge methods** — squash or rebase only (no merge commits, matching linear-history requirement)

> **Note:** For a solo maintainer project, the `required_approving_review_count: 1`
> creates a loop since you can't approve your own PR. Either: (a) edit to `0` for
> solo flow, (b) add `bypass_actors` for your user, or (c) open a 2nd GitHub
> account for reviews.

### `release-tag-protection.json`

Applied to tags matching `v*` (semver release tags).

- **Block deletion** — published tags are immutable; download links stay valid
- **Block force push** — can't move a tag to a different commit after release
- **Block update** — can't overwrite an existing tag (covers the `nightly` mutable tag
  case — if you want nightly to be mutable, exclude it in `conditions.ref_name.exclude`
  with `refs/tags/nightly`)
