"""The Graph `fields` lists vlab reads Meta objects with — defined once.

These were `server/meta.py` constants until `authoring/templates.py` needed the
same lists: a template ad this repo *creates* has to be readable through
`GET /{org}/meta/ads`, and the only way to assert that without a live Meta
account is for the builder and the proxy to name the same fields. Two copies of
`CREATIVE_FIELDS` would have been two definitions of what a study deploys —
exactly the duplication `adopt/confs.py` was extracted to stop
(planning/agent-study-authoring.md §7, "one implementation").

**`fields` is the contract, not the path.** What is in `CREATIVE_FIELDS` is
exactly what ends up stored as `creatives[].template` and therefore what gets
deployed, so a "tidy-up" that drops a field silently changes what studies ship.
`server/test_meta.py` asserts the literal for that reason; keep it that way.

Lives at the top of the package rather than under `facebook/` or `server/`
because both of those are imported by things the other side must not pull in:
`server/*` drags FastAPI and psycopg into a pipx-installed CLI, and
`facebook/state.py` is the retry/reconciliation half of the Meta integration,
which the authoring library deliberately does not use (§13.4). This module
imports nothing.
"""

# `dashboard/src/helpers/api.ts:487` — 'name, id, account_id'. The spaces are
# dropped here (Graph tolerates them, but they are an accident of the JS
# literal, not part of the contract).
AD_ACCOUNT_FIELDS = "name,id,account_id"

# api.ts:517
CAMPAIGN_FIELDS = "name,id"

# api.ts:549. `targeting` is the load-bearing one: it is the entire input to
# `adopt.authoring.extract.extract_from_adset`, which needs `id` and
# `targeting` and uses `name` for error messages.
ADSET_FIELDS = "name,id,targeting"

# api.ts:583-595, verbatim and in the same order. This list is what ends up
# stored as a creative `template`, so adding or removing a field here changes
# what a study deploys. `contextual_multi_ads` is in the request but not in the
# dashboard's `Ad` TypeScript interface; `effective_instagram_story_id` and
# `instagram_actor_id` are in the interface but not in the request. The request
# is what actually runs, so the request is what is reproduced.
CREATIVE_FIELD_LIST = [
    "id",
    "name",
    "actor_id",
    "asset_feed_spec",
    "degrees_of_freedom_spec",
    "effective_instagram_media_id",
    "effective_object_story_id",
    "instagram_user_id",
    "object_story_spec",
    "contextual_multi_ads",
    "thumbnail_url",
]

CREATIVE_FIELDS = ",".join(CREATIVE_FIELD_LIST)

# api.ts:598 — the creative arrives NESTED under each ad, via field expansion,
# not as a second request.
AD_FIELDS = f"id,name,creative{{{CREATIVE_FIELDS}}}"

# The subset of `CREATIVE_FIELD_LIST` that `marketing._create_creative` reads
# off a stored template when it builds a study's real ad, plus the one
# `audiences.hydrate_audiences` reads. Anything here that a template ad does
# not carry is a template that cannot deploy — which is why
# `authoring.templates` checks a created creative against this list rather than
# against the whole read list. `id`, `name`, `thumbnail_url`,
# `effective_*` and `contextual_multi_ads` are read but not required:
# `_create_creative` copies them only `if field in config.template`.
#
#   actor_id            audiences.py:150 — `template["actor_id"]`, a bare
#                       KeyError if absent, and the page every custom audience
#                       is scoped to.
#   object_story_spec   the creative itself. `_create_creative` indexes it
#                       unconditionally (`config.template["object_story_spec"]`).
REQUIRED_TEMPLATE_CREATIVE_FIELDS = ["actor_id", "object_story_spec"]
