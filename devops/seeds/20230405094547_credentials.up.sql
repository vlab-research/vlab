INSERT INTO credentials 
  (user_id, entity, key, details)
VALUES
  (
    'auth0|6412f8baa95e852045477d6e',
    'typeform',
    'Foo Bar TypeForm',
    '{
        "key": "supersecret"
    }'
  ),
  (
    'auth0|6412f8baa95e852045477d6e',
    'alchemer',
    'Foo Bar Alchemer',
    '{
        "api_token": "supersecret",
        "api_token_secret": "supersecret"
    }'
  ),
  (
    'auth0|6412f8baa95e852045477d6e',
    'fly',
    'Fly Credentials',
    '{
        "api_key": "supersecret"
    }'
  );
