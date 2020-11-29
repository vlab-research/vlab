import React, { useEffect } from 'react';
import { Route, Redirect, useRouteMatch } from 'react-router-dom';
import PropTypes from 'prop-types';
import { Typeform } from '../../services';
import { CreateBtn, Container } from '../UI';
import TypeformCreateForm from './TypeformCreateForm';

const { handleAuthorization } = Typeform;

const TypeformCreate = ({ cb, children }) => {
  const match = useRouteMatch();

  return (
    <Container>
      <CreateBtn to={`${match.url}/from-typeform`}>{children}</CreateBtn>
      <Route path={`${match.path}/from-typeform`}>
        <TypeformCreateForm cb={cb} />
      </Route>
    </Container>
  );
};

export const TypeformCreateAuth = ({ location, match, history }) => {
  const code = location.search && location.search.match(/([A-Z,0-9])\w+/)[0];

  useEffect(() => {
    if (code) handleAuthorization({ code, history, match });
  }, [code]);

  if (!code) return <Redirect to="/surveys/create" />;

  return null;
};

TypeformCreate.propTypes = {
  cb: PropTypes.func.isRequired,
  children: PropTypes.node.isRequired,
};

TypeformCreateAuth.propTypes = {
  match: PropTypes.objectOf(PropTypes.any).isRequired,
  history: PropTypes.objectOf(PropTypes.any).isRequired,
  location: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default TypeformCreate;
