INSERT INTO orgs
  (id, name)
VALUES
  ('90840745-4996-42bb-aa42-05a41936e6e0', 'demo organisation');

INSERT INTO users
  (id)
VALUES
  /*This is the demo@vlab.digital user and attached to an org*/
  ('auth0|6412f8baa95e852045477d6e'),
  /*This is an invalid user you cant login with but we use it to check if org
   * level resources are accessible via the demo user*/
  ('auth0|111111111111111111111111');

INSERT INTO orgs_lookup
  (user_id, org_id)
VALUES
  ('auth0|111111111111111111111111', '90840745-4996-42bb-aa42-05a41936e6e0'),
  ('auth0|6412f8baa95e852045477d6e', '90840745-4996-42bb-aa42-05a41936e6e0');
