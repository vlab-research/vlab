

DROP TABLE IF EXISTS studies;
CREATE TABLE studies(
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    name string NOT NULL,
    slug string NOT NULL,
    CONSTRAINT unique_name UNIQUE(name),
    CONSTRAINT unique_slug UNIQUE(slug)
);

INSERT INTO studies 
  (name, slug, created) 
VALUES 
  ('Iron overload in men', 'iron-overload-in-men', '2021-01-03'),
  ('Consuming carbs less often leads to better fat adaptation', 'consuming-carbs-less-often-leads-to-better-fat-adaptation', '2021-01-02'),
  ('Most used programming language for api development', 'most-used-programming-language-for-api-development', '2021-01-04');