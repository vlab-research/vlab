'use strict';

const { Response } = require('../../queries');

exports.getAll = async ctx => {
  try {
    ctx.body = await Response.all();
    ctx.status = 200;
  } catch (err) {
    console.error(err);
    ctx.body = 500;
  }
};
