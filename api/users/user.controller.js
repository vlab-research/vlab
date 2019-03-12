'use strict';

const { User } = require('../../queries');

exports.getAll = async ctx => {
  ctx.body = await User.all();
  ctx.status = 200;
};
