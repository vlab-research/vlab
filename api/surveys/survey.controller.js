'use strict';

const { Survey } = require('../../queries');
const { User } = require('../../queries');
const { SurveyUtil } = require('../../utils');
const { TypeformUtil } = require('../../utils');

exports.postOne = async (req, res) => {
  try {
    const { formid, title } = req.body;
    const { email } = req.user;

    const user = await User.user({ email });
    if (!user[0])
      return res.status(404).json({ error: `User ${email} does not exist!` });

    const { id: userid, token } = user[0];

    const form = await TypeformUtil.TypeformForm(token, formid);
    const messages = await TypeformUtil.TypeformMessages(token, formid);

    // userid should be actual id...
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

exports.getBy = async (req, res, next) => {
  try {
    const { pageid, shortcode } = req.query;

    if (pageid && shortcode) {
      const surveys = await Survey.retrieveByPage({ pageid, code: shortcode });
      if (surveys.length > 1) {
        // TODO: remove once shit actually works
        throw new Error('WTF? More than one survey??? ');
      }
      res.status(200).send(surveys[0]);
    } else {
      next();
    }
  } catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
};

exports.getAll = async (req, res) => {
  try {
    const { email } = req.user;

    if (!email) {
      return res.status(404).send('No user, no survey!');
    }

    const surveys = await Survey.retrieve({ email });
    res.status(200).send(surveys);
  } catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
};
