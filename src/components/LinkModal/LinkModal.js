import React, { useState } from 'react';
import PropTypes from 'prop-types';
import * as s from './style';
import { PrimaryBtn, SecondaryBtn } from '../UI';

const Actions = ({
  success, selected, back,
}) => {
  const handleClick = (e) => {
    e.preventDefault();
    success(selected);
  };

  return (
    <s.ActionsBtns>
      <SecondaryBtn onClick={(e) => { e.preventDefault(); back(); }} type="text">
        Cancel
      </SecondaryBtn>
      <PrimaryBtn onClick={handleClick} type="text">Create</PrimaryBtn>
    </s.ActionsBtns>
  );
};


Actions.propTypes = {
  success: PropTypes.func.isRequired,
  selected: PropTypes.object.isRequired,
  back: PropTypes.func.isRequired,
};


const LinkModal = ({
  dataSource, renderItem, title, loading, back, success, footer, fallbackText, initialSelection = {},
}) => {
  const closeModal = ({ target, currentTarget }) => target === currentTarget && back();

  const [selected, setSelected] = useState(initialSelection);

  return (
    <s.Modal onClick={closeModal}>
      <s.ModalBox>
        { loading ? (<s.Spinner />) : (
          <>
            <s.ModalHeader />
            <s.ModalTitle>
              {' '}
              {title}
              {' '}
            </s.ModalTitle>
            <s.List>
              {dataSource.length ? dataSource.map((item, index) => (
                <s.ListItem
                  key={item.id}
                  active={item.id === selected.id}
                  onClick={() => setSelected(state => ({ ...state, ...item }))}
                >
                  {renderItem(item, index)}
                </s.ListItem>
              )) : (
                <s.ListItem>
                  {' '}
                  {fallbackText}
                  {' '}
                </s.ListItem>
              )}
            </s.List>
            <s.ModalFooter>
              {footer(selected)}
              <Actions {...{ success, selected, back }} />
            </s.ModalFooter>
          </>
        )}
      </s.ModalBox>
    </s.Modal>
  );
};


LinkModal.s = s;

LinkModal.propTypes = {
  success: PropTypes.func.isRequired,
  back: PropTypes.func.isRequired,
  renderItem: PropTypes.func.isRequired,
  footer: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  initialSelection: PropTypes.object,
  title: PropTypes.string.isRequired,
  fallbackText: PropTypes.string.isRequired,
  dataSource: PropTypes.array,
};

export default LinkModal;
