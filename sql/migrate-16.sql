ALTER TABLE chatroach.responses ADD COLUMN translated_response VARCHAR;

created,
form_json,
survey_name,
translation_conf,

    WITH t AS
      (SELECT
       FROM surveys
       WHERE id = %s
       LIMIT 1)
    SELECT surveys.id
    FROM t
    LEFT JOIN surveys
    ON surveys.survey_name = survey_name
    AND surveys.metadata = jsonb_set(metadata, ARRAY[(translation_conf->>'field')], translation_conf->'reference')
    ORDER BY surveys.created
    LIMIT 1
