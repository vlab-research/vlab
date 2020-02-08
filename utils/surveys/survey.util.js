'use strict';

const joi = require('joi');

function validate(reqData) {
  const formSchema = joi
    .object({
      formid: joi
        .string()
        .alphanum()
        .required(),
      userid: joi.string().required(),
      messages: joi.string(),
      shortcode: joi
        .string()
        .required(),
      title: joi.string().required(),
      form: joi.string().required(),
    })
    .unknown()
    .required();

  const { error } = joi.validate(reqData, formSchema);
  if (error) {
    throw new Error(
      `Config validation error: ${error.message}. Data: ${JSON.stringify(
        reqData,
        null,
        2,
      )}`,
    );
  }
}

module.exports = {
  validate,
};
