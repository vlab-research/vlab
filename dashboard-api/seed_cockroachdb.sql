
DROP TABLE IF EXISTS optimization_reports;
DROP TABLE IF EXISTS studies;
DROP TABLE IF EXISTS users;

CREATE TABLE users(
  id string PRIMARY KEY
);

INSERT INTO users
  (id)
VALUES
  ('auth0|61916c1dab79c900713936de'),
  ('auth0|47016c1dab79c900713937fa');


CREATE TABLE studies(
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id string NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    name string NOT NULL,
    slug string NOT NULL,
    CONSTRAINT unique_study_name_for_user UNIQUE(user_id, name),
    CONSTRAINT unique_study_slug_for_user UNIQUE(user_id, slug)
);

INSERT INTO studies
  (name, slug, created, id, user_id)
VALUES
  ('Iron overload in men', 'iron-overload-in-men', '2021-01-03', '36634740-0a26-44a3-b69d-d1338af5126c', 'auth0|61916c1dab79c900713936de'),
  ('Consuming carbs less often leads to better fat adaptation', 'consuming-carbs-less-often-leads-to-better-fat-adaptation', '2021-01-02', 'f6112068-5227-4e17-b255-2b80df8745e9', 'auth0|61916c1dab79c900713936de'),
  ('Most used programming language for api development', 'most-used-programming-language-for-api-development', '2021-01-04', 'a5601576-08d9-486b-adc9-9b981b7f103b', 'auth0|47016c1dab79c900713937fa');


CREATE TABLE optimization_reports(
  study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
  created TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  report_type VARCHAR NOT NULL,
  details JSON NOT NULL,
  CONSTRAINT unique_report UNIQUE(study_id, created)
);

INSERT INTO optimization_reports
  (study_id, created, report_type, details)
VALUES
  ('36634740-0a26-44a3-b69d-d1338af5126c', '2021-01-03', 'FACEBOOK_ADOPT','{
    "25-spain-male": {
      "current_budget": 720000,
      "desired_percentage": 5,
      "current_percentage": 0,
      "expected_percentage": 0,
      "desired_participants": null,
      "current_participants": 0,
      "expected_participants": 0,
      "current_price_per_participant": 0
    },
    "25-spain-female": {
      "current_budget": 720000,
      "desired_percentage": 5,
      "current_percentage": 0,
      "expected_percentage": 0,
      "desired_participants": 2400,
      "current_participants": 0,
      "expected_participants": 0,
      "current_price_per_participant": 0
    }
  }'),
  ('36634740-0a26-44a3-b69d-d1338af5126c', '2021-01-04', 'FACEBOOK_ADOPT','{
    "25-spain-male": {
      "current_budget": 720000,
      "desired_percentage": 5,
      "current_percentage": 8.25,
      "expected_percentage": 8.67,
      "desired_participants": null,
      "current_participants": 59,
      "expected_participants": 64,
      "current_price_per_participant": 100
    },
    "25-spain-female": {
      "current_budget": 720000,
      "desired_percentage": 5,
      "current_percentage": 3.5,
      "expected_percentage": 2.98,
      "desired_participants": 2400,
      "current_participants": 25,
      "expected_participants": 22,
      "current_price_per_participant": 300
    }
  }');
