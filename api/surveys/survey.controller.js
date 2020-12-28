'use strict';

const { Survey, User, Credential } = require('../../queries');
const { SurveyUtil } = require('../../utils');
const { TypeformUtil } = require('../../utils');

exports.postOne = async (req, res) => {
  try {
    // add more keys
    const { survey_name, formid, title, shortcode, metadata, translation_conf } = req.body;
    const { email } = req.user;

    if (!(email && formid && shortcode && survey_name)) {
      return res
        .status(400)
        .send(
          `Missing shit!: formid: ${formid}, shortcode: ${shortcode}`,
        );
    }

    // TODO: this is silly, get userid via db query
    const user = await User.user({ email });
    if (!user)
      return res.status(404).json({ error: `User ${email} does not exist!` });
    const { id: userid } = user;

    const cred = await Credential.getOne({email, entity: 'typeform_token', key: TypeformUtil.makeKey(email)});
    const token = cred.details.access_token;

    const form = await TypeformUtil.TypeformForm(token, formid);
    const messages = await TypeformUtil.TypeformMessages(token, formid);

    // check if translation is possible with formcentral
    const err = await SurveyUtil.validateTranslation({form, translation_conf})
    if (err) {
      return res.status(400).send('Translation config not valid. Error: ' + err)
    }

    const created = new Date();

    // add good stuff here
    const survey = {
      formid,
      created,
      messages,
      title,
      userid, // TODO: change userid for teamid
      form,
      shortcode,
      survey_name,
      metadata,
      translation_conf,
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
      const survey = surveys[0]
      if (survey) {
        return res.status(200).send(survey);
      }
      return res.status(404).json({error: {message: 'survey not found'}})

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
      return res.status(400).send('No user, no survey!');
    }

    const surveys = await Survey.retrieve({ email });
    res.status(200).send(surveys);
  } catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
};
