ALTER TABLE chatroach.responses ADD COLUMN translated_response VARCHAR;

ALTER TABLE chatroach.surveys ADD COLUMN metadata JSONB NOT NULL DEFAULT '{}';
ALTER TABLE chatroach.surveys ADD COLUMN survey_name VARCHAR NOT NULL DEFAULT 'default';
ALTER TABLE chatroach.surveys ADD COLUMN translation_conf JSONB NOT NULL DEFAULT '{}';


update surveys set metadata = metadata || '{"language": "english"}' where shortcode like '%eng';
update surveys set metadata = metadata || '{"language": "odia"}' where shortcode like '%odi';
update surveys set metadata = metadata || '{"language": "hindi"}' where shortcode like '%hin';
-- update surveys set metadata = metadata || '{"language": "hindi"}' where shortcode like '%hinexc';

-- update surveys set metadata = metadata || '{"wave": 0}' where shortcode like 'baseline%';

-- update surveys set metadata = metadata || '{"wave": 1}' where shortcode like 'follow1%';

-- update surveys set metadata = metadata || '{"wave": 2}' where shortcode like 'follow2%';
-- update surveys set metadata = metadata || '{"wave": 3}' where shortcode like 'follow3%';
-- update surveys set metadata = metadata || '{"wave": 4}' where shortcode like 'follow4%';
-- update surveys set metadata = metadata || '{"wave": 5}' where shortcode like 'follow5%';
update surveys set metadata = metadata || '{"wave": 6}' where shortcode like 'follow6%';

-- update surveys set metadata = metadata || '{"version": 2}' where created > date '2020-09-21' and shortcode like 'follow3%';
