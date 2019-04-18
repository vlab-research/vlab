import React from 'react';
import { Route } from 'react-router-dom';
import PropTypes from 'prop-types';
import Typeform from '../../services/Typeform';
import { TypeformBtn } from './style';

const { createOrAuthorize, handleAuthorization } = new Typeform();

const TypeformCreate = ({ match, history }) => {
  return (
    <div>
      <TypeformBtn onClick={() => createOrAuthorize(history)}>CREATE</TypeformBtn>
      <Route
        path={`${match.path}/auth`}
        render={({ location }) => {
          const code = location.search.match(/([A-Z,0-9])\w+/)[0];
          handleAuthorization(code, history);
          return <div> LOADING PAGE AUTH </div>;
        }}
      />
      <Route
        path={`${match.path}/create`}
        render={() => {
          return <div> CREATE NEW SURVEY </div>;
        }}
      />
    </div>
  );
};

TypeformCreate.propTypes = {
  match: PropTypes.objectOf(PropTypes.any).isRequired,
  history: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default TypeformCreate;
