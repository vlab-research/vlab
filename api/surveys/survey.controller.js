'use strict';

const { Survey } = require('../../queries');
const { validate } = require('../../utils/survey.util');

exports.postOne = async (req, res) => {
  try {
    const { formid, form, shortcode } = req.body;
    const survey = {
      formid,
      form,
      shortcode,
      userid: req.user.email,
    };

    validate(survey);
    const createdSurvey = await Survey.create(survey);

    res.status(201).send(createdSurvey);
  } catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
};
