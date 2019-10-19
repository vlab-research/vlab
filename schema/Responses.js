/* global cube */
cube(`Responses`, {
  sql: `SELECT * FROM responses`,

  measures: {
    count: {
      type: `count`,
    },

    uniqueUserCount: {
      sql: `userid`,
      type: `countDistinct`,
    },

    startTime: {
      type: `min`,
      sql: `timestamp`,
    },

    endTime: {
      type: `max`,
      sql: `timestamp`,
    },
  },

  dimensions: {
    formid: {
      type: `string`,
      sql: `surveyid`,
    },

    userid: {
      type: `string`,
      sql: `userid`,
    },

    flowid: {
      type: `string`,
      sql: `flowid`,
    },

    timestamp: {
      type: `time`,
      sql: `timestamp`,
    },

    response: {
      type: `string`,
      sql: `response`,
    },

    questionId: {
      type: `string`,
      sql: `question_idx`,
    },
  },
});
