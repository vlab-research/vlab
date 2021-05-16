'use strict';
const { Readable } = require('stream');

const { Response } = require('../../queries');
const { ResponseUtil } = require('../../utils');


function handle(err, res) {
  console.error(err)
  res.status(500).end()
}

exports.getAll = async (req, res) => {
  try {
    const responses = await Response.all();
    res.status(200).send(responses);
  } catch (err) {
    handle(err, res)
  }
};


function handleCsvResponse (dataStream, filename, res) {
  res.header('Content-Type', 'text/csv');
  res.header(
    'Content-Disposition',
    `attachment; filename="${filename}_${new Date().toISOString()}.csv"`,
  );

  res.status(200);

  const csv = ResponseUtil.toCSV();

  csv.on('error', err => handle(err, res));
  dataStream.on('error', err => handle(err, res));

  dataStream
    .pipe(csv)
    .pipe(res);
}

exports.getResponsesCSV = async (req, res) => {
  const { survey } = req.query;
  const { email } = req.user;
  try {

    const responseStream = await Response.formResponses(email, decodeURIComponent(survey));
    handleCsvResponse(responseStream, 'responses', res);

  } catch (err) {
    handle(err, res)
  }
};

// TODO: move to surveys route...
exports.getFormDataCSV = async (req, res) => {
  const { survey } = req.query;
  const { email } = req.user;

  try {

    const data = await Response.formData(email, decodeURIComponent(survey));
    const dataStream = Readable.from(data);
    handleCsvResponse(dataStream, survey, res);

  } catch (err) {
    handle(err, res)
  }
};
