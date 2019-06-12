'use strict';

const { Survey } = require('../../queries');
const { User } = require('../../queries');
const { SurveyUtil } = require('../../utils');
const { TypeformUtil } = require('../../utils');

exports.postOne = async (req, res) => {
  try {
    const { formid, title } = req.body;
    const { email:userid } = req.user;
  
    const user = await User.user({email: userid});
    if (!user[0]) return res.status(401).send();

    const form = await TypeformUtil.TypeformForm(user[0].token, formid);
    const shortcode = await SurveyUtil.shortcode(userid);
    const survey = {formid, title, userid, form, shortcode};
    
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
    const { email:userid } = req.user;
    if (!userid) return res.status(401).send();

    const surveys = await Survey.retrieve({userid});
    res.status(201).send(surveys);
  } catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
};
