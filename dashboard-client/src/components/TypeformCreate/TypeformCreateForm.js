import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import moment from 'moment';
import { useHistory } from 'react-router-dom';
import typeformAuth from '../../services/typeform';
import LinkModal from '../LinkModal';

const { createOrAuthorize } = typeformAuth;

const TypeformCreateForm = ({ cb }) => {
  const history = useHistory();
  const [forms, setForms] = useState([]);

  useEffect(() => {
    createOrAuthorize()
      .then(({ items }) => items && setForms(items))
      .catch(e => console.error(e)); //eslint-disable-line
  }, []);

  return (
    <LinkModal
      title="Choose Your Form"
      initialSelection={{ id: '', title: '' }}
      fallbackText="You don't have any forms in Typeform! Please make a form first, then you will be able to import it here."
      success={cb}
      loading={!forms.length}
      back={() => history.go(-1)}
      dataSource={forms}
      footer={selected => (
        <LinkModal.s.Selected>
          <LinkModal.s.SelectedInfo>{`selected: ${selected.id}`}</LinkModal.s.SelectedInfo>
          <LinkModal.s.SelectedInfo>{`title: ${selected.title}`}</LinkModal.s.SelectedInfo>
        </LinkModal.s.Selected>
      )}
      renderItem={item => (
        <>
          <LinkModal.s.ListItemTitle>
            {item.title}
            <LinkModal.s.ListItemDate>
              {' '}
              {`${moment(item.last_updated_at).format('Do MMM YY')}`}
              {' '}
            </LinkModal.s.ListItemDate>
          </LinkModal.s.ListItemTitle>
          <LinkModal.s.ListItemId>{item.id}</LinkModal.s.ListItemId>
        </>
      )}

    />
  );
};


TypeformCreateForm.propTypes = {
  cb: PropTypes.func.isRequired,
};

export default TypeformCreateForm;
