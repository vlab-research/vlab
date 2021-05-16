/* global cube */
cube(`LastQuestions`, {
  sql: `
    with t as (
    select r.*,
    ROW_NUMBER() OVER (PARTITION BY r.userid, r.parent_surveyid ORDER BY timestamp DESC) as n
    FROM responses
    )
    SELECT *
    FROM t
    WHERE n = 1
    `,

  measures: {
    count: {
      type: `count`,
    }
  },

  dimensions: {
    formid: {
      type: `string`,
      sql: `surveyid`,
    },

    timestamp: {
      type: `time`,
      sql: `timestamp`,
    },

    response: {
      type: `string`,
      sql: `response`,
    },

    questionRef: {
      type: `string`,
      sql: `question_ref`,
    },

    questionText: {
      type: `string`,
      sql: `question_text`,
    },
  },
});
