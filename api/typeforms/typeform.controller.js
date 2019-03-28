'use strict';

const Typeform = require('../../utils/typeform.util');

exports.postOne = async (req, res) => {
  try {
    const { formid, form, shortcode } = req.body;
    const typeform = {
      formid,
      form,
      shortcode,
      userid: req.user.email,
    };
    Typeform.validate(typeform);
    // TODO: create the resource into the database

    res.status(201).send(/* TODO: send back the newly creted resource */);
  } catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
};
