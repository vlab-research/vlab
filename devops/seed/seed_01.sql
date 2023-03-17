/*
 * This is a seed file that will be run AFTER the database
 * has been setup. There should be no altering of schemas in here
 * all updates should be done in the normal SQL file.
 *
 * Please try keep all resources pertaining to the demo user
 * unless there is specific value of testing with different users
 */

INSERT INTO users
  (id)
VALUES
  /*This is the demo@vlab.digital user*/
  ('auth0|6412f8baa95e852045477d6e');


INSERT INTO studies
  (name, slug, created, id, user_id)
VALUES
  (
    'Iron overload in men', 
    'iron-overload-in-men', 
    '2021-01-03', 
    '36634740-0a26-44a3-b69d-d1338af5126c', 
    'auth0|6412f8baa95e852045477d6e'
  ),
  (
    'Consuming carbs less often leads to better fat adaptation', 
    'consuming-carbs-less-often-leads-to-better-fat-adaptation', 
    '2021-01-02', 
    'f6112068-5227-4e17-b255-2b80df8745e9', 
    'auth0|6412f8baa95e852045477d6e'
  ),
  (
    'Most used programming language for api development', 
    'most-used-programming-language-for-api-development', 
    '2021-01-04', 
    'a5601576-08d9-486b-adc9-9b981b7f103b', 
    'auth0|6412f8baa95e852045477d6e'
  );


