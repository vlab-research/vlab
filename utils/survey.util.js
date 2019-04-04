'use strict';

const joi = require('joi');

function validate(reqData) {
  const formSchema = joi
    .object({
      formid: joi
        .string()
        .alphanum()
        .required(),
      userid: joi
        .string()
        .email()
        .required(),
      shortcode: joi
        .string()
        .length(4, 'utf8')
        .regex(/^[0-9]+$/)
        .required(),
      form: joi.string().required(),
    })
    .unknown()
    .required();

  const { error } = joi.validate(reqData, formSchema);
  if (error) {
    throw new Error(`Config validation error: ${error.message}`);
  }
}

module.exports = {
  validate,
};
