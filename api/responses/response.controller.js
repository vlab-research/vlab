'use strict';

const { Response } = require('../../queries');
const { ResponseUtil } = require('../../utils');

exports.getAll = async (req, res) => {
  try {
    const responses = await Response.all();
    res.status(200).send(responses);
  } catch (err) {
    console.error(err);
    res.status(500).end();
  }
};


exports.getResponsesCSV = async (req, res) => {
  const { survey } = req.query;
  try {
    res.header('Content-Type', 'text/csv');
    res.header(
      'Content-Disposition',
      `attachment; filename="responses_${new Date().toISOString()}.csv"`,
    );

    // Hoping this helps avoid problems with proxy timeouts
    // TODO: check if query is OK first???
    res.writeHead(200);

    const responseStream = await Response.formResponses(decodeURIComponent(survey));

    responseStream
      .pipe(ResponseUtil.toCSV())
      .pipe(res);

  } catch (err) {
    console.error(err);
    res.status(500).end();
  }
};
