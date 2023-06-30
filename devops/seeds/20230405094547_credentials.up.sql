INSERT INTO credentials 
  (user_id, entity, key, details)
VALUES
  (
    'auth0|6412f8baa95e852045477d6e',
    'typeform',
    'typeform-test',
    '{
        "key": "supersecret"
    }'
  ),
  (
    'auth0|6412f8baa95e852045477d6e',
    'alchemer',
    'alchemer*!',
    '{
        "api_token": "supersecret",
        "api_token_secret": "supersecret"
    }'
  ),
  (
    'auth0|6412f8baa95e852045477d6e',
    'fly',
    'fly 123',
    '{
        "api_key": "supersecret"
    }'
  );
