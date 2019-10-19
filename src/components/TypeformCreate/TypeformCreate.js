import React, { useEffect } from 'react';
import { Route, Redirect } from 'react-router-dom';
import PropTypes from 'prop-types';
import { Typeform } from '../../services';
import { TypeformBtn, Container } from './style';
import TypeformCreateForm from './TypeformCreateForm';

const { handleAuthorization } = Typeform;

const TypeformCreate = ({ match }) => {
  return (
    <Container>
      <TypeformBtn to={`${match.path}/create`}>CREATE</TypeformBtn>
      <Route path={`${match.path}/auth`} render={props => <TypeformCreateAuth {...props} />} />
      <Route path={`${match.path}/create`} render={props => <TypeformCreateForm {...props} />} />
    </Container>
  );
};

const TypeformCreateAuth = ({ location, match, history }) => {
  const code = location.search && location.search.match(/([A-Z,0-9])\w+/)[0];

  useEffect(() => {
    if (code) handleAuthorization({ code, history, match });
  }, [code]);

  if (!code) return <Redirect to={`/${match.path.split('/')[0]}`} />;

  return <div> LOADING PAGE AUTH </div>;
};

TypeformCreate.propTypes = {
  match: PropTypes.objectOf(PropTypes.any).isRequired,
  history: PropTypes.objectOf(PropTypes.any).isRequired,
};

TypeformCreateAuth.propTypes = {
  match: PropTypes.objectOf(PropTypes.any).isRequired,
  history: PropTypes.objectOf(PropTypes.any).isRequired,
  location: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default TypeformCreate;
