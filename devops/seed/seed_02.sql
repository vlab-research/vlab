/*
 * As study confs is an append only table we need seed data
 * to represent the idea of any update will just be equivalent with a new row
 * in the database
 */
INSERT INTO study_confs
  (study_id, created, conf_type, conf)
VALUES
  (
    'a5601576-08d9-486b-adc9-9b981b7f103b',
    '2023-03-20 13:13:21.132',
    'general',
    '{
        "ad_account": "",
        "destination_type": "MESSENGER",
        "extra_metadata": {},
        "instagram_id": "",
        "min_budget": 1,
        "name": "most-used-programming-language-for-api-development",
        "objective": "MESSAGES",
        "opt_window": 48,
        "optimization_goal": "REPLIES",
        "page_id": ""
    }'
  ),
  (
    'a5601576-08d9-486b-adc9-9b981b7f103b',
    '2023-03-21 13:13:21.132',
    'general',
    '{
        "ad_account": "123456789",
        "destination_type": "MESSENGER",
        "extra_metadata": {},
        "instagram_id": "123456789",
        "min_budget": 1,
        "name": "most-used-programming-language-for-api-development",
        "objective": "MESSAGES",
        "opt_window": 48,
        "optimization_goal": "REPLIES",
        "page_id": "1234567898765432"
    }'
  ),
  (
    'a5601576-08d9-486b-adc9-9b981b7f103b',
    '2023-03-21 13:13:21.132',
    'creatives',
    '[{
        "body": "FooBar",
        "button_text": "Foobar",
        "destination": "fly",
        "image_hash": "8ef11493ade6deced04f36b9e8cf3900",
        "link_text": "Foobar",
        "name": "Ad1_Recruitment",
        "tags": null,
        "welcome_message": "welcome"
      },
      {
        "body": "FooBar",
        "button_text": "Foobar",
        "destination": "fly",
        "image_hash": "8ef11493ade6deced04f36b9e8cf3900",
        "link_text": "Foobar",
        "name": "Ad2_Recruitment",
        "tags": null,
        "welcome_message": "welcome"
      },
      {
        "body": "FooBar",
        "button_text": "Foobar",
        "destination": "fly",
        "image_hash": "8ef11493ade6deced04f36b9e8cf3900",
        "link_text": "Foobar",
        "name": "Ad3_Recruitment",
        "tags": null,
        "welcome_message": "welcome"
      }]'
  );