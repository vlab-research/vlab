import React from 'react';
import PropTypes from 'prop-types';
import './FormConfig.css';


const FormConfig = ({ form }) => (
  <div>
    {form.shortcode}
    {' '}
      v
    {form.version}
  </div>
);

FormConfig.propTypes = {
  form: PropTypes.objectOf(PropTypes.object).isRequired,
};

export default FormConfig;
