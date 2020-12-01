import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import moment from 'moment';
import { useHistory } from 'react-router-dom';
import * as s from './style';
import typeformAuth from '../../services/typeform';
import { PrimaryBtn, SecondaryBtn } from '../UI';

const { createOrAuthorize } = typeformAuth;

const TypeformCreateForm = ({ cb }) => {
  const history = useHistory();
  const [forms, setForms] = useState([]);
  const [selectedForm, setSelectedForm] = useState({ title: '', id: '' });

  useEffect(() => {
    createOrAuthorize()
      .then(({ items }) => items && setForms(items))
      .catch(e => console.error(e)); //eslint-disable-line
  }, []);

  const closeModal = ({ target, currentTarget }) => target === currentTarget && history.go(-1);

  return (
    <s.Modal onClick={closeModal}>
      <s.ModalBox>
        { forms.length ? (
          <>
            <s.ModalHeader />
            <Main {...{
              forms, selectedForm, setSelectedForm,
            }}
            />
            <s.ModalFooter>
              <s.Selected>
                <s.SelectedInfo>{`selected: ${selectedForm.id}`}</s.SelectedInfo>
                <s.SelectedInfo>{`title: ${selectedForm.title}`}</s.SelectedInfo>
              </s.Selected>
              <Actions {...{
                cb, selectedForm, history,
              }}
              />
            </s.ModalFooter>
          </>
        )
          : (<s.Spinner />)}
      </s.ModalBox>
    </s.Modal>
  );
};

const Main = ({
  forms, selectedForm, setSelectedForm,
}) => <ChooseFormId {...{ forms, selectedForm, setSelectedForm }} />;

const ChooseFormId = ({ forms, selectedForm, setSelectedForm }) => (
  forms.length && (
  <>
    <s.ModalTitle> Choose Your Form </s.ModalTitle>
    <s.List>
      {forms.map(item => (
        <s.ListItem
          active={item.id === selectedForm.id}
          onClick={() => setSelectedForm(state => ({ ...state, ...item }))}
          key={item.id}
        >
          <s.ListItemTitle>
            {item.title}
            <s.ListItemDate>
              {`${moment(item.last_updated_at).format('Do MMM YY')}`}
            </s.ListItemDate>
          </s.ListItemTitle>
          <s.ListItemId>{item.id}</s.ListItemId>
        </s.ListItem>
      ))}
    </s.List>
  </>
  )
);

const Actions = ({
  cb, selectedForm, history,
}) => {
  const handleClick = (e) => {
    e.preventDefault();
    cb({ formid: selectedForm.id, title: selectedForm.title });
    history.go(-1);
  };

  return (
    <s.ActionsBtns>
      <SecondaryBtn onClick={(e) => { e.preventDefault(); history.go(-1); }} type="text">
        Cancel
      </SecondaryBtn>
      <PrimaryBtn onClick={handleClick} type="text">Create</PrimaryBtn>
    </s.ActionsBtns>
  );
};

Main.propTypes = {
  selectedForm: PropTypes.objectOf(PropTypes.any).isRequired,
  setSelectedForm: PropTypes.func.isRequired,
  forms: PropTypes.arrayOf(PropTypes.object).isRequired,
};

ChooseFormId.propTypes = {
  forms: PropTypes.arrayOf(PropTypes.object).isRequired,
  selectedForm: PropTypes.objectOf(PropTypes.any).isRequired,
  setSelectedForm: PropTypes.func.isRequired,
};


Actions.propTypes = {
  cb: PropTypes.func.isRequired,
  history: PropTypes.objectOf(PropTypes.any).isRequired,
  selectedForm: PropTypes.objectOf(PropTypes.any).isRequired,
};


TypeformCreateForm.propTypes = {
  cb: PropTypes.func.isRequired,
};

export default TypeformCreateForm;
