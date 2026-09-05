-- Second half of 20260904000000_api_token_hardening. See that file for the
-- model and for why this is a separate migration (CockroachDB will not index a
-- column added in the same transaction).

-- Partial: every non-api_token row and every legacy api_token row has a NULL
-- jti, and none of them belong in this index.
--
-- STORING makes the verifier's hot path — jti -> owner + scopes + expiry — an
-- index-only read. user_id and org_id are NOT implicit here: `credentials` has
-- no declared primary key, so CockroachDB's implicit PK is the hidden `rowid`
-- and nothing else rides along for free.
--
-- UNIQUE is an integrity guard rather than a requirement: jti is a server-side
-- uuid4, so a duplicate means a bug, and this turns that bug into an error
-- instead of an ambiguous lookup.
--
CREATE UNIQUE INDEX IF NOT EXISTS unique_api_token_jti
    ON credentials (api_token_jti)
    STORING (details, user_id, org_id, key)
    WHERE api_token_jti IS NOT NULL;

-- The legacy-tombstone lookup, and the "list my keys" query, both filter on
-- (user_id, entity). unique_entity_key_per_user already covers that prefix, so
-- there is deliberately no second index here.
