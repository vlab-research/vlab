'use strict';
const { Credential } = require('../../queries');
const { TypeformUtil } = require('../../utils');


exports.authorize = async (req, res) => {
  try {
    const r = await TypeformUtil.TypeformToken(req.params.code);
    if (!r.access_token) {
      return res.status(500).json(r)
    }

    const {email} = req.user;


    const data = { entity: 'typeform_token', key: TypeformUtil.makeKey(email), details: r, email };

    const cred = await Credential.create(data)
    res.status(201).json(cred);

  } catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
};

exports.getForm = async (req, res) => {
  try {
    const {email} = req.user;
    const cred = await Credential.getOne({email, entity: 'typeform_token', key: TypeformUtil.makeKey(email)})

    if (!cred) return res.status(401).send('Do not have Typeform Token for user');
    const token = cred.details.access_token

    if (!token) return res.status(401).send('Do not have Typeform Token for user');

    const forms = await TypeformUtil.TypeformFormList(token);

    res.status(200).send(forms);
  } catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
};
