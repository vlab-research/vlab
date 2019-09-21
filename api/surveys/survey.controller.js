'use strict';

const { Survey } = require('../../queries');
const { User } = require('../../queries');
const { SurveyUtil } = require('../../utils');
const { TypeformUtil } = require('../../utils');

exports.postOne = async (req, res) => {
  try {
    const { formid, title } = req.body;
    const { email: userid } = req.user;

    const user = await User.user({ email: userid });
    if (!user[0])
      return res.status(404).json({ error: `User ${userid} does not exist!` });

    const form = await TypeformUtil.TypeformForm(user[0].token, formid);
    const messages = await TypeformUtil.TypeformMessages(user[0].token, formid);

    const shortcode = await SurveyUtil.shortcode(userid);
    const survey = { formid, messages, title, userid, form, shortcode };

    SurveyUtil.validate(survey);
    const createdSurvey = await Survey.create(survey);

    res.status(201).send(createdSurvey);
  } catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
};

exports.getAll = async (req, res) => {
  try {
    const { email: userid } = req.user;
    const user = await User.user({ email: userid });

    // Users don't exist before they make a survey.
    // So if the user doesn't exist, send no surveys!
    if (!user[0]) return res.status(200).json([]);

    const surveys = await Survey.retrieve({ userid });
    res.status(200).send(surveys);
  } catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
};
