-- Reverse of 20260904000000_api_token_hardening.up.sql.
--
-- Bounded loss: the api_token / api_token_revoked ROWS survive untouched — they
-- are ordinary credentials rows — and only the derived column goes. The column
-- holds no state of its own, so re-running the up migration reconstructs it
-- from `details` exactly as it was.
--
-- What DOES change while the column is absent is behaviour: with no jti column
-- the verifier cannot find a row for a v2 token, so every hardened key stops
-- authenticating. Down-migrating is therefore a real outage for agent keys, not
-- a no-op. Legacy keys are unaffected.
--
-- The index is dropped by the 20260904000001 down, which golang-migrate runs
-- first.

ALTER TABLE credentials DROP COLUMN IF EXISTS api_token_jti;
