'use strict';
const { User } = require('../../queries');
const { TypeformUtil } = require('../../utils');

exports.authorize = async (req, res) => {
  try {
    const token = await TypeformUtil.TypeformToken(req.params.code);
    const user = { token: token.access_token, email: req.user.email };
    (await User.update(user)) || (await User.create(user));
    res.status(200).send();
  } catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
};

exports.getForm = async (req, res) => {
  try {
    const user = await User.user({ email: req.user.email });
    if (!user[0]) return res.status(401).send();
    const forms = await TypeformUtil.TypeformFormList(user[0].token);
    res.status(200).send(forms);
  } catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
};
