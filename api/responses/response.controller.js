'use strict';
const { Readable } = require('stream');

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

function handle(err, res) {
  console.error(err.message)
  res.status(500).end()
}

function handleCsvResponse (dataStream, filename, res) {
  res.header('Content-Type', 'text/csv');
  res.header(
    'Content-Disposition',
    `attachment; filename="${filename}_${new Date().toISOString()}.csv"`,
  );

  res.status(200);

  const csv = ResponseUtil.toCSV();

  // TODO: test this error handling!
  csv.on('error', handle);
  dataStream.on('error', handle);

  dataStream
    .pipe(csv)
    .pipe(res);
}

exports.getResponsesCSV = async (req, res) => {
  const { survey } = req.query;
  try {

    const responseStream = await Response.formResponses(decodeURIComponent(survey));
    handleCsvResponse(responseStream, 'responses', res);

  } catch (err) {
    console.error(err);
    res.status(500).end();
  }
};

// TODO: move to surveys route...
exports.getFormDataCSV = async (req, res) => {
  const { survey } = req.query;
  try {

    const data = await Response.formData(decodeURIComponent(survey));
    const dataStream = Readable.from(data);
    handleCsvResponse(dataStream, survey, res);

  } catch (err) {
    console.error(err);
    res.status(500).end();
  }
};
