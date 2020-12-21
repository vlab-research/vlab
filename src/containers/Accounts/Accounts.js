import React from 'react';
import PropTypes from 'prop-types';
import FacebookPages from '../FacebookPages';

const pages = (res) => {
  console.log(res); // eslint-disable-line no-console
};

const Accounts = ({  }) => {
  return (<FacebookPages callback={pages} />)
}

Accounts.propTypes = {};

export default Accounts;
