'use strict';

const { Survey } = require('../../queries');
const { User } = require('../../queries');
const { SurveyUtil } = require('../../utils');
const { TypeformUtil } = require('../../utils');

exports.postOne = async (req, res) => {
  try {
    // Get teamid
    const { formid, title, shortcode } = req.body;
    const { email } = req.user;

    if (!(email && formid && title && shortcode)) {
      return res
        .status(400)
        .send(
          `Missing shit!: formid: ${formid}, title: ${title}, shortcode: ${shortcode}`,
        );
    }

    const user = await User.user({ email });
    if (!user)
      return res.status(404).json({ error: `User ${email} does not exist!` });

    const { id: userid, token } = user;

    const form = await TypeformUtil.TypeformForm(token, formid);
    const messages = await TypeformUtil.TypeformMessages(token, formid);

    const created = new Date();
    const survey = {
      formid,
      created,
      messages,
      title,
      userid, // TODO: change userid for teamid
      form,
      shortcode,
    };

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
    const { pageid, shortcode, timestamp } = req.query;

    if (pageid && shortcode && timestamp) {
      const surveys = await Survey.retrieveByPage({
        pageid,
        code: shortcode,
        timestamp,
      });

      // send only latest survey...
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
