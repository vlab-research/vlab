#!/usr/bin/env bash
# scripts/release.sh — tag, push, watch CI, and verify image landed in GHCR.
#
# Refuses to exit 0 unless the release workflow has actually pushed the image
# to ghcr.io/vlab-research/<service>:<version>. This is the hardening against
# the May 19 2026 incident where 4 source-*-v0.1.1 tags were pushed but the
# release workflow never fired, leaving prod cronjobs in ImagePullBackOff for 8
# days. See planning/release-process.md.
#
# Usage:
#   scripts/release.sh <service> <version>          # tag HEAD, push, watch
#   scripts/release.sh <service> <version> <sha>    # tag a specific commit
#   scripts/release.sh --force <service> <version>  # delete+recreate tag
#
# Examples:
#   scripts/release.sh source-typeform v0.1.2
#   scripts/release.sh adopt v0.1.68 30bd7a8
#   scripts/release.sh --force swoosh v0.1.6 HEAD
#
# Required:
#   - gh CLI authenticated with repo + packages:write scope
#   - clean or committed working tree (use --allow-dirty to skip)
#   - on main or a release branch (axe that branch restriction in this file if
#     you want feature-branch releases)

set -euo pipefail

ALLOW_DIRTY=0
FORCE=0
if [[ "${1:-}" == "--allow-dirty" ]]; then ALLOW_DIRTY=1; shift; fi
if [[ "${1:-}" == "--force" ]];      then FORCE=1;    shift; fi

if [[ $# -lt 2 || $# -gt 3 ]]; then
    sed -n '2,17p' "$0"
    exit 64
fi

SERVICE="$1"
VERSION="$2"
SHA="${3:-HEAD}"

# Mirror release.yml's case statement — keeps the script enforcing the same
# set of known services.
KNOWN_SERVICES=(api adopt source-typeform source-alchemer source-fly source-qualtrics swoosh vlab-migrations)
if [[ ! " ${KNOWN_SERVICES[*]} " =~ " ${SERVICE} " ]]; then
    echo "error: service '$SERVICE' not in known list:" >&2
    printf '  %s\n' "${KNOWN_SERVICES[@]}" >&2
    echo "  add it to .github/workflows/release.yml AND this list together" >&2
    exit 65
fi

# Version: must look like vMAJOR.MINOR.PATCH. The release.yml pattern is
# '*-v[0-9]+.[0-9]+.[0-9]+' but we cannot use shell regex the same way; bash
# globmatch is enough here.
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "error: version '$VERSION' must match vMAJOR.MINOR.PATCH (e.g. v0.1.2)" >&2
    exit 65
fi

TAG="${SERVICE}-${VERSION}"

# ---------- pre-flight ----------

if [[ "$ALLOW_DIRTY" -eq 0 ]]; then
    if ! git diff --quiet HEAD 2>/dev/null || ! git diff --cached --quiet HEAD 2>/dev/null; then
        echo "error: working tree dirty. commit/stash first, or pass --allow-dirty" >&2
        exit 66
    fi
fi

command -v gh >/dev/null || { echo "error: gh CLI not installed" >&2; exit 67; }
gh auth status >/dev/null 2>&1 || { echo "error: gh not authenticated. run 'gh auth login'" >&2; exit 67; }

REMOTE="$(git remote get-url origin 2>/dev/null || true)"
if [[ "$REMOTE" != *vlab-research/vlab* ]]; then
    echo "error: origin is '$REMOTE', expected something containing vlab-research/vlab" >&2
    exit 68
fi

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
    if [[ "$FORCE" -eq 0 ]]; then
        echo "error: tag '$TAG' already exists. delete it or pass --force" >&2
        exit 69
    fi
    git tag -d "$TAG"
    git push origin --delete "$TAG" 2>/dev/null || true
fi

if ! git rev-parse -q --verify "$SHA^{commit}" >/dev/null; then
    echo "error: '$SHA' is not a commit" >&2
    exit 70
fi

# ---------- tag + push ----------

COMMIT="$(git rev-parse "$SHA^{commit}")"
echo ">> creating annotated tag $TAG at $COMMIT"
git tag -a "$TAG" "$COMMIT" -m "Release $SERVICE $VERSION"

echo ">> git push origin $TAG"
git push origin "$TAG"

echo ">> waiting for release workflow to be queued (max 90s)"
RUN_ID=""
DEADLINE=$((SECONDS + 90))
while [[ $SECONDS -lt $DEADLINE ]]; do
    # Look across the most recent N runs (default is the latest 20 anyway),
    # then ask jq to find the first whose headBranch matches our tag. 'first'
    # returns null on no match; the ' // empty' makes that empty so `[[ -n ]]`
    # works the way a bash user expects.
    RUN_ID=$(gh run list --workflow=release.yml --limit 30 \
        --json databaseId,headBranch \
        | jq -r "first(.[] | select(.headBranch == \"$TAG\") | .databaseId | tostring) // empty")
    [[ -n "$RUN_ID" ]] && break
    sleep 5
done
if [[ -z "$RUN_ID" ]]; then
    echo "FATAL: no workflow run was queued for $TAG after 90s." >&2
    echo "       This is exactly the failure mode from the May 19 incident." >&2
    echo "       Do NOT bump any values files until you figure out why the" >&2
    echo "       workflow did not trigger. See planning/release-process.md." >&2
    exit 71
fi

echo ">> watching run $RUN_ID"
gh run watch "$RUN_ID" --exit-status
CONCLUSION=$(gh run view "$RUN_ID" --json conclusion --jq .conclusion)
if [[ "$CONCLUSION" != "success" ]]; then
    echo "FATAL: workflow concluded '$CONCLUSION'. Image was NOT published." >&2
    echo "       inspect: gh run view $RUN_ID --log-failed" >&2
    exit 72
fi

# ---------- verify image landed ----------

IMAGE="ghcr.io/vlab-research/$SERVICE:$VERSION"
echo ">> verifying $IMAGE is pullable"
# GHCR's registry v2 API does NOT accept a raw `gh auth token` as a Bearer: you
# must first exchange it at the token endpoint and use the returned short-lived
# token to read the manifest. Passing the PAT straight through returns 403 even
# when the image exists — that used to make `make release` exit 73 spuriously
# (observed on the vlab-migrations-v0.1.0 release, whose image was in fact
# pushed fine). See planning/migration-job-fix.md.
#
# Note: the "workflow concluded success" check above (the CI `push: true` step)
# is the authoritative signal that the image landed. This manifest lookup is a
# secondary confirmation, so an inability to *obtain* a token warns rather than
# blocks; only a token that then gets a non-200 manifest is fatal.
TOKEN_ENDPOINT="https://ghcr.io/token?service=ghcr.io&scope=repository:vlab-research/$SERVICE:pull"
GH_TOKEN_VAL="$(gh auth token 2>/dev/null || true)"
if [[ -n "$GH_TOKEN_VAL" ]]; then
    # Basic-auth the exchange so PRIVATE packages verify too; harmless for public.
    BEARER=$(curl -sS -u "x-access-token:$GH_TOKEN_VAL" "$TOKEN_ENDPOINT" | jq -r '.token // empty')
else
    # Anonymous exchange — sufficient for public images.
    BEARER=$(curl -sS "$TOKEN_ENDPOINT" | jq -r '.token // empty')
fi
if [[ -z "$BEARER" ]]; then
    echo "WARN: could not obtain a GHCR pull token; skipping manifest verify." >&2
    echo "      CI concluded success above, which is the authoritative signal." >&2
else
    HTTP=$(curl -sS -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $BEARER" \
        -H "Accept: application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.docker.distribution.manifest.v2+json" \
        "https://ghcr.io/v2/vlab-research/$SERVICE/manifests/$VERSION")
    if [[ "$HTTP" != "200" ]]; then
        echo "FATAL: GHCR manifest lookup returned HTTP $HTTP for $IMAGE" >&2
        echo "       CI was green but the manifest isn't readable. If the package" >&2
        echo "       is private, your gh token may lack read:packages — confirm in" >&2
        echo "       the GHCR UI before bumping any values file." >&2
        exit 73
    fi
fi

echo ""
echo "OK: $TAG released."
echo "    workflow: https://github.com/vlab-research/vlab/actions/runs/$RUN_ID"
echo "    image:    $IMAGE"
echo ""
echo "next step: only NOW is it safe to bump devops/values/*.yaml to $VERSION."
