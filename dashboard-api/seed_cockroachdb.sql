

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
  (name, slug) 
VALUES 
  ('Iron overload in men', 'iron-overload-in-men'),
  ('Consuming carbs less often leads to better fat adaptation', 'consuming-carbs-less-often-leads-to-better-fat-adaptation');