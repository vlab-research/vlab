import React from 'react';
import PropTypes from 'prop-types';

import './Navbar.css';

const Navbar = ({ auth, history }) => {
  return (
    <div className="navbar-container">
      <h1>Here goes the menu!</h1>
      <button type="button" onClick={() => auth.logout(history)}>
        Logout!
      </button>
    </div>
  );
};

Navbar.propTypes = {
  auth: PropTypes.objectOf(PropTypes.any).isRequired,
  history: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default Navbar;
