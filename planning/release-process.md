# Release Process

> Why this doc exists. **Never bump `devops/values/*.yaml` until the image it
> points at is confirmed published to GHCR.** A commit on May 19 2026 broke
> prod cronjobs for 8 days by doing exactly that.

## TL;DR

```
scripts/release.sh <service> <version>            # tag, push, watch, verify
                  ... bump devops/values/*.yaml   # only after above prints "OK"
helm upgrade ...                                 # deploy
```

Or, when manually pushing tags:

```
make tag SERVICE=source-typeform VERSION=v0.1.2  # creates and pushes tag
make release-wait SERVICE=source-typeform VERSION=v0.1.2  # polls gh run + GHCR
```

## When to release

Cut a release whenever you have merged code you want deployed to staging or
prod. The repo deploys via Docker images pinned to semantic-version tags. The
release pipeline is the contract — if it succeeds, you have a deployable
artifact; if it fails, you don't.

Three releaseable services have separate impls but share the workflow:
`source-typeform`, `source-alchemer`, `source-fly`, `source-qualtrics`
(inference-based, parameterized by `APP_PATH`). Plus `adopt`, `api`,
`swoosh`. Adding a new service means both an entry in `.github/workflows/release.yml`'s
case statement **and** a line in `scripts/release.sh`'s `KNOWN_SERVICES`
array. Keep them in sync.

## The canonical sequence

1. **Commit your code first.** The tag points at a commit — that's the
   artifact. Don't tag uncommitted work.
2. **Push the tag.** Either `git push origin source-typeform-v0.1.2` directly,
   or use `scripts/release.sh source-typeform v0.1.2`.
3. **The release workflow fires automatically.** It builds the Docker image
   and pushes it to `ghcr.io/vlab-research/<service>:<version>`.
4. **Verify it landed.** `scripts/release.sh` does this for you. Manually:
   - `gh run list --workflow=release.yml` — the new run should appear within
     ~60s.
   - `gh run watch <id> --exit-status` — block until green.
   - `gh run view <id>` — the published image digest.
   - GHCR web UI: `https://github.com/vlab-research/vlab/pkgs/container/<image>`.
5. **THEN bump `devops/values/*.yaml`.** Prereq: the image must exist in
   GHCR or pods will go `ImagePullBackOff` on the next cron tick.
6. **THEN helm deploy.** `helm upgrade ...` with the bumped values.

The order is non-negotiable. If you push a tag and no workflow run is queued
within 90s, **stop** — do not bump values. That's the failure mode (see
"Lessons" below).

## Why versioned tags instead of `:latest`

`:latest` is mutable and silently changes between scheduled cron runs.
Cronjobs run `pullPolicy: Always`, so they will unwittingly pull a rewritten
image that may include unrelated changes. Pinned version tags:

- Make rollouts deterministic.
- Make rollbacks a one-line values change.
- Match how `adopt`, `api`, and `swoosh` are already shipped.

`:latest` is still published on pushes to `main` for the connector sources
via `.github/workflows/inference.yaml`. Use it for development only — never
in values committed to git.

## Tag scheme

Tags are `<image-name>-v<MAJOR>.<MINOR>.<PATCH>`, e.g. `source-typeform-v0.1.2`.
The image name and the tag prefix match (with the exception of `api` →
`vlab-dashboard-api`). The matching prefix means the image a tag pushes is
unambiguous from the tag name alone, and the v-prefix keeps the tag sortable.

Validate locally:

```
git tag --list | rg '^source-typeform-v[0-9.]+$' | sort -V
```

Bumping the major number is for breaking-change connector protocol changes.
Bump the minor for added functionality. Patch for bug fixes. Same semver
contract as before, with the tag prefix ceremony added.

## CI contracts (the parts that broke)

`release.yml` is plain and linear. It:

1. Triggers on `push` of any tag matching `*-v[0-9]+.[0-9]+.[0-9]+` *or*
   `workflow_dispatch`. Dispatch is the manual-rerun path: pick the tag in
   the "Use workflow from" ref selector.
2. Parses the tag into `service=image-name-without-v...` and
   `version=v<MAJOR>.<MINOR>.<PATCH>`.
3. Resolves the build context, Dockerfile, and image name from a case
   statement. **Any new service must be added here.**
4. Builds with `docker/build-push-action@v5` and pushes.

Why CI contracts are the bits that matter:

- The trigger pattern is the only thing that decides whether a `git push
  origin <tag>` will fire a workflow. If a tag is created via the GitHub
  API rather than `git push`, the webhook delivery is occasionally missed
  (we believe this is what happened on May 19).
- The case statement is the single source of truth on which services are
  supported. A service added to `scripts/release.sh` but not to
  `release.yml` will publish an empty case branch and the job will exit
  nonzero.

## Made-up issues to watch for

### "I tagged & pushed, but `gh run list` is empty after 60s"

The May 19 failure mode. **Do not bump values.** Instead:

1. Check `git ls-remote origin $TAG` confirms the tag is on the remote.
2. Open GitHub Actions → release and look for any in-progress run started
   in the past 5 minutes — rare, but can race.
3. If still nothing, hit `workflow_dispatch` against the same tag —
   `release.yml` explicitly supports this. The job parses `GITHUB_REF_NAME`
   the same way for both `push` and `dispatch`.
4. If dispatch also fails, investigate the case statement / Dockerfile for
   that service.

### "Workflow succeeded but pods still pull old image"

Probably `pullPolicy: IfNotPresent` or the cache. Cronjobs currently use
`pullPolicy: Always` in values — verify both that the values file has
`Always` and that `kubectl get pod -o jsonpath='{.spec.containers[*].imagePullPolicy}'`
confirms it.

### "Workflow conclusion was 'failure'"

Look at logs: `gh run view <id> --log-failed`. The two recurring classes are:

- Build context / Dockerfile error: usually the `APP_PATH` env var or a
  missing `COPY` path.
- Registry auth: the `secrets.GITHUB_TOKEN` doesn't have `packages: write`
  scope or the action step is misconfigured.

### "I bumped values and pods went ImagePullBackOff"

`scripts/check-imagepullbackoff.sh` should be wired to alert on this case
so it doesn't sit for 8 days. But the immediate fix is **revert the values
bump** (`git revert <bump-sha>`) and only re-apply once the image is
confirmed in GHCR.

## Operational hooks

- `scripts/release.sh <service> <version>` — the entry point for releases.
  Tags, pushes, watches the GH Actions run, fails loudly if the image
  doesn't appear in GHCR. Exits non-zero in any failure mode worth
  investigating.
- `scripts/check-imagepullbackoff.sh [--age M] [--slack-webhook URL]` —
  scan all namespaces for stale ImagePullBackOff pods. Returns nonzero
  when any pods are stuck for more than `M` minutes (default 5). Designed
  to be wired into a CronJob or external scheduler.
- `make tag` / `make release-wait` — convenience wrappers around the
  scripts. Install once, runs forever.

## Lessons from the May 19 incident

Commit: [`4c43833`](https://github.com/vlab-research/vlab/commit/4c43833b87ba1e1e2347c6d5a0b98a03c9bbc58a) — `chore(devops): bump source-* images to v0.1.1 in toixo-prod`. Co-authored: Claude Opus 4.7.

What happened:

- `999b09d1` fixed the connector grace-window bug and was tagged
  `source-{typeform,alchemer,fly,qualtrics}-v0.1.1`. The release workflow
  should have fired for each tag.
- The tags landed on `origin` (`git ls-remote` confirmed) but no release
  workflow runs were created. GitHub Actions ran 12 times the month of May
  but none of those 4. The first 4 of those 12 (`source-*-v0.1.0`) had fired
  minutes earlier with no issue; the next run was `adopt-v0.1.67` on June 8.
- 3 minutes after the tag push, the values bump landed. It assumed the
  images had been published. Helm applied → cronjobs went
  `ImagePullBackOff` → sat there for 8 days → noticed because we
  grepped for ImagePullBackOff manually.

Why our process was wrong, not the tooling:

- The release workflow does not include a `tests` step. It would have
  caught a build failure at image-build time, but the actual problem was
  upstream (a webhook didn't fire), which the workflow couldn't have
  detected either way.
- Nothing was monitoring for `ImagePullBackOff`. Manual greps were the
  only signal, and they require a human noticing.
- The tag push and the values bump were separate commits, 3 minutes
  apart, with no assertion that the tag push produced an image before the
  bump.

What we changed:

- `scripts/release.sh` now refuses to exit 0 unless the image is in GHCR.
- `scripts/check-imagepullbackoff.sh` makes `ImagePullBackOff >= 5m` an
  alertable condition, not a thing humans have to grep for.
- This doc codifies the order: tag → push → image exists → bump values →
  deploy. Anything else is by definition a regression of May 19.
