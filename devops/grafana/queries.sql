------------------------------------------------------------
-- Stratum targets
------------------------------------------------------------
WITH tt AS
  (WITH t AS
    (SELECT row_to_json(json_each(details)) d
    FROM (SELECT details, adopt_reports.created
          FROM adopt_reports
          JOIN campaigns ON campaignid = campaigns.id
          WHERE campaigns.NAME = '$campaign'
          ORDER BY created DESC
          LIMIT 1))
  SELECT d->>'key' AS stratum,
  (d->'value'->>'goal')::FLOAT AS goal,
  (d->'value'->>'expected_share')::FLOAT as expected_share,
  (d->'value'->>'respondent_share')::FLOAT AS current_share,
  (d->'value'->>'budget')::FLOAT AS budget
  FROM t)
SELECT *, goal - current_share AS current_gap
FROM tt
ORDER BY current_gap DESC;

------------------------------------------------------------
-- Optimization loss over time
------------------------------------------------------------

WITH tt AS
  (WITH t AS
    (SELECT row_to_json(json_each(details)) d, created
     FROM (SELECT details, adopt_reports.created
          FROM adopt_reports
          JOIN campaigns ON campaignid = campaigns.id
          WHERE campaigns.NAME = '$campaign'))
  SELECT
      created,
      (d->'value'->>'goal')::FLOAT AS goal,
      (d->'value'->>'respondent_share')::FLOAT AS share
  FROM t)
SELECT $__time(created), sqrt(SUM(CASE WHEN dif < 0 THEN 0 ELSE dif^2 END)) / count(*)::FLOAT AS dif
FROM (SELECT created, goal - share AS dif FROM tt)
WHERE
  $__timeFilter(created)
GROUP BY created
ORDER BY created;


------------------------------------------------------------
-- Current average deviation
------------------------------------------------------------

WITH tt AS
  (WITH t AS
    (SELECT row_to_json(json_each(details)) d, created
     FROM (SELECT details, adopt_reports.created
          FROM adopt_reports
          JOIN campaigns ON campaignid = campaigns.id
          WHERE campaigns.NAME = '$campaign'
          ORDER BY created DESC
          LIMIT 1))
  SELECT
      created,
      (d->'value'->>'goal')::FLOAT AS goal,
      (d->'value'->>'respondent_share')::FLOAT AS share
  FROM t)
SELECT created, AVG(ABS(goal - share)) AS dif
FROM tt;


------------------------------------------------------------
-- Config
------------------------------------------------------------

WITH t AS
     (SELECT row_to_json(json_each_text(conf->0)) AS d
     FROM (SELECT *
          FROM campaign_confs
          JOIN campaigns ON campaignid=id
          WHERE conf_type = 'opt' AND NAME = 'vaccination-wbg'
          ORDER BY campaign_confs.created
          DESC LIMIT 1)
     )
SELECT d->>'key' AS KEY, d->>'value' AS VALUE FROM t;

-------------------------------------------------------------
-- Average responses, grouped by other responses
-------------------------------------------------------------
with tt as (WITH t AS (
  SELECT
    *,
    ROW_NUMBER() OVER (PARTITION BY question_ref, userid, surveyid
                       ORDER BY timestamp DESC) as n
  FROM responses
  WHERE question_ref in ('caste', 'fever4months')
  AND shortcode in ('extrabasehin1shot', 'extrabasehin')
)
SELECT userid, translated_response, question_ref
FROM t
WHERE n = 1)
SELECT gr, avg(res) as mean, sqrt(variance(res)/count(*)) as std_dev, count(*)
FROM (SELECT userid, ARRAY_AGG(translated_response order by question_ref) as gr FROM tt WHERE question_ref in ('caste', ) GROUP BY userid)
INNER JOIN (SELECT userid, (CASE WHEN translated_response = 'Yes' THEN 1 ELSE 0 END) as res from tt WHERE question_ref = 'fever4months')
USING (userid)
where ARRAY_LENGTH(gr, 1) = ARRAY_LENGTH(ARRAY('caste', ), 1)
GROUP BY gr;
