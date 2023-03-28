CREATE TABLE IF NOT EXISTS orgs(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      name string UNIQUE
);

/*We need a lookup table to handle many to many relations*/
CREATE TABLE IF NOT EXISTS orgs_lookup(
      org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
      user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE
);

/*We need to drop the index before adding in to make this statement 
 * idempotent.
 * This is to validate that we dont have duplicate refernces to the same
 * user/org link*/
DROP INDEX IF EXISTS orgs_lookup@unique_org_lookup_reference CASCADE;
ALTER TABLE orgs_lookup
ADD CONSTRAINT unique_org_lookup_reference
UNIQUE(user_id, org_id);

/* We also need to add the org id wherever the user id is due to the fact that 
 * and organisation will own the study, not the users, so if a user gets
 * removed from an organisation they should still be able to fetch studies
 * created by that user
 *
 * We dont enforce a constraint as we currenlt will have studies without orgs
 * etc
 * */
ALTER TABLE studies
ADD COLUMN org_id UUID;

ALTER TABLE inference_data
ADD COLUMN org_id UUID;

ALTER TABLE credentials
ADD COLUMN org_id UUID;

