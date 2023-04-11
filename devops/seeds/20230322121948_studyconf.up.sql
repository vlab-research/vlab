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
        "min_budget": 1.50,
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
        "min_budget": 1.50,
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
    'recruitment',
    '{
      "ad_campaign_name": "vlab-most-used-prog-1",
      "budget": 10000,
      "end_date": "2022-08-05T00:00:00",
      "max_sample": 1000,
      "start_date": "2022-07-26T00:00:00"
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
  ),
  (
    
    'a5601576-08d9-486b-adc9-9b981b7f103b',
    '2023-03-21 13:13:21.132',
    'destinations',
    '[
      {
        "name": "typeform",
        "url_template": "https://example.typeform.com/to/ABCDEF?ref={ref}"
      },
      {
        "initial_shortcode": "foobarbaz",
        "name": "fly"
      }
    ]'
  ),
  (
    'a5601576-08d9-486b-adc9-9b981b7f103b',
    '2023-03-21 13:13:21.132',
    'audiences',
    '[
      {
        "lookalike": null,
        "name": "foobar-baz",
        "partitioning": null,
        "question_targeting": null,
        "subtype": "CUSTOM"
      },
      {
        "lookalike": {
          "spec": {
            "country": "US",
            "ratio": 0.1,
            "starting_ratio": 0.0
          },
          "target": 100
          },
        "name": "foobar-baz-qux",
        "partitioning": null,
        "question_targeting": {
          "op": "not_equal",
          "vars": [
            {
              "type": "variable",
              "value": "hcw"
            },
            {
              "type": "constant",
              "value": "E"
            }
          ]
        },
        "subtype": "LOOKALIKE"
      }
    ]'
  );
