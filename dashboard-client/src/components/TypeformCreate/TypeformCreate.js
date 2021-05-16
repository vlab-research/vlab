import React, { useEffect } from 'react';
import { Route, useRouteMatch } from 'react-router-dom';
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

export const TypeformCreateAuth = ({ location, history }) => {
  const code = location.search && location.search.match(/([A-Z,0-9])\w+/)[0];

  useEffect(() => {
    if (code) {
      handleAuthorization(code)
        .then(() => {
          // crazy hack to deal with all the "backs"
          // in other components...
          history.push('/surveys');
          history.push('/surveys/create');
          history.push('/surveys/create/from-typeform');
        });
    }
  }, [code]);

  return (<div> spinner </div>);
};

TypeformCreate.propTypes = {
  cb: PropTypes.func.isRequired,
  children: PropTypes.node.isRequired,
};

TypeformCreateAuth.propTypes = {
  history: PropTypes.objectOf(PropTypes.any).isRequired,
  location: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default TypeformCreate;
