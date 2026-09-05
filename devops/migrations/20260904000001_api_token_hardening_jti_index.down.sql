-- Reverse of 20260904000001_api_token_hardening_jti_index.up.sql.
--
-- The index has to go before the column (dropped by the 20260904000000 down),
-- because CockroachDB refuses to drop a column an index depends on without
-- CASCADE — and CASCADE would take the index silently, whether or not that was
-- intended. golang-migrate applies downs newest-first, so that ordering is
-- automatic.

DROP INDEX IF EXISTS credentials@unique_api_token_jti;
