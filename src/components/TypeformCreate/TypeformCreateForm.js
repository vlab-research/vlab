import React, { useState, useEffect, useContext } from 'react';
import PropTypes from 'prop-types';
import moment from 'moment';
import { Survey } from '../../containers/Surveys/Surveys';

import * as s from './style';
import typeformAuth from '../../services/Typeform';

const { createOrAuthorize, createSurvey } = typeformAuth;

const TypeformCreateForm = ({ history, match }) => {
  const { setSurveys } = useContext(Survey);
  const [forms, setForms] = useState([]);
  const [selectedForm, setSelectedForm] = useState({ title: '', id: '' });
  const [state, setState] = useState(1);

  useEffect(() => {
    createOrAuthorize()
      .then(({ items }) => items && setForms(items))
      .catch(e => console.error(e)); //eslint-disable-line
  }, []);

  const closeModal = ({ target, currentTarget }) =>
    target === currentTarget && history.push(`/${match.path.split('/')[1]}`);

  return (
    !!forms.length && (
      <s.Modal onClick={closeModal}>
        <s.ModalBox {...{ state }}>
          <s.ModalHeader />
          <Main {...{ forms, selectedForm, setSelectedForm, state }} />
          <s.ModalFooter>
            <s.Selected>
              <s.SelectedInfo>{`selected: ${selectedForm.id}`}</s.SelectedInfo>
              <s.SelectedInfo>{`title: ${selectedForm.title}`}</s.SelectedInfo>
            </s.Selected>
            <Actions {...{ selectedForm, state, setState, history, match, setSurveys }} />
          </s.ModalFooter>
        </s.ModalBox>
      </s.Modal>
    )
  );
};

const Main = ({ forms, selectedForm, setSelectedForm, state }) => {
  switch (state) {
    case 1:
      return <ChooseFormId {...{ forms, selectedForm, setSelectedForm }} />;
    case 2:
      return <SetFormTitle {...{ forms, selectedForm, setSelectedForm }} />;
    default:
      return null;
  }
};

const ChooseFormId = ({ forms, selectedForm, setSelectedForm }) => {
  return (
    forms.length && (
      <>
        <s.ModalTitle> Choose Your Form </s.ModalTitle>
        <s.List>
          {forms.map(item => (
            <s.ListItem
              active={item.id === selectedForm.id}
              onClick={() => setSelectedForm(item)}
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
};

const SetFormTitle = ({ selectedForm, setSelectedForm }) => {
  const [title, setTitle] = useState(selectedForm.title);
  return (
    <>
      <s.ModalTitle> Select your title </s.ModalTitle>
      <s.TitleInput
        value={title}
        onChange={({ target }) => {
          if (target.value.length < 50) {
            setTitle(target.value);
            setSelectedForm(state => ({ ...state, title: target.value }));
          }
        }}
      />
    </>
  );
};

const Actions = ({ selectedForm: { id, title }, state, setState, history, match, setSurveys }) => {
  const handleSubmit = async () => {
    const survey = id && (await createSurvey({ id, title, history, match }));
    setSurveys(surveys => [...survey, ...surveys]);
  };
  switch (state) {
    case 1:
      return (
        <s.ActionsBtns>
          <s.SecondaryBtn onClick={() => history.push(`/${match.path.split('/')[1]}`)}>
            Cancel
          </s.SecondaryBtn>
          <s.PrimaryBtn onClick={() => id && setState(2)}>Choose</s.PrimaryBtn>
        </s.ActionsBtns>
      );
    case 2:
      return (
        <s.ActionsBtns>
          <s.SecondaryBtn onClick={() => setState(1)}>Back</s.SecondaryBtn>
          <s.PrimaryBtn onClick={handleSubmit}>Create</s.PrimaryBtn>
        </s.ActionsBtns>
      );
    default:
      return null;
  }
};

Main.propTypes = {
  selectedForm: PropTypes.objectOf(PropTypes.any).isRequired,
  setSelectedForm: PropTypes.func.isRequired,
  forms: PropTypes.arrayOf(PropTypes.object).isRequired,
  state: PropTypes.number.isRequired,
};

ChooseFormId.propTypes = {
  forms: PropTypes.arrayOf(PropTypes.object).isRequired,
  selectedForm: PropTypes.objectOf(PropTypes.any).isRequired,
  setSelectedForm: PropTypes.func.isRequired,
};

SetFormTitle.propTypes = {
  selectedForm: PropTypes.objectOf(PropTypes.any).isRequired,
  setSelectedForm: PropTypes.func.isRequired,
};

Actions.propTypes = {
  state: PropTypes.number.isRequired,
  setState: PropTypes.func.isRequired,
  setSurveys: PropTypes.func.isRequired,
  match: PropTypes.objectOf(PropTypes.any).isRequired,
  history: PropTypes.objectOf(PropTypes.any).isRequired,
  selectedForm: PropTypes.objectOf(PropTypes.any).isRequired,
};

export default TypeformCreateForm;
