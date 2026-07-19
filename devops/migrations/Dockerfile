# devops/migrations/Dockerfile — the vlab-migrations image.
#
# Bakes the golang-migrate CLI together with this repo's SQL migrations into a
# versioned artifact (ghcr.io/vlab-research/vlab-migrations:<tag>). The chart's
# pre-upgrade hook Job (devops/helm/templates/migrations.yaml) runs this image
# with `-database <cockroach url> up` to apply pending migrations before new
# pods roll. See planning/migration-job-fix.md.
#
# The connection string is deliberately NOT baked in: the same image runs
# against any environment; the DB coordinates come from Job args (values) at
# runtime.
FROM migrate/migrate:v4.15.2

# `migrate` is already the image's entrypoint; we only add our SQL. golang-migrate
# reads -path non-recursively, so the inittest/ and initvlab/ subdirs copied here
# are inert to `migrate up` (they hold fresh-cluster bootstrap SQL only).
COPY . /migrations
