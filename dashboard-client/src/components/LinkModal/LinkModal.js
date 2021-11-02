import React, { useState } from 'react';
import PropTypes from 'prop-types';
import * as s from './style';
import { PrimaryBtn, SecondaryBtn } from '../UI';

const Actions = ({
  success, successText, selected, back,
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
      <PrimaryBtn onClick={handleClick} type="text">{ successText }</PrimaryBtn>
    </s.ActionsBtns>
  );
};


Actions.propTypes = {
  success: PropTypes.func.isRequired,
  successText: PropTypes.string,
  selected: PropTypes.object.isRequired,
  back: PropTypes.func.isRequired,
};


const LinkModal = ({
  content, dataSource, renderItem, title, loading, back,
  success, successText, footer, fallbackText, initialSelection = {},
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
              { content ? content 
              : dataSource.length ? dataSource.map((item, index) => (
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
                )
              }
            </s.List>
            <s.ModalFooter>
              { footer ? footer(selected)
              : <LinkModal.s.Selected></LinkModal.s.Selected> }
              <Actions {...{ success, successText, selected, back }} />
            </s.ModalFooter>
          </>
        )}
      </s.ModalBox>
    </s.Modal>
  );
};


LinkModal.s = s;

LinkModal.defaultProps = {
  successText: "Create"
};

LinkModal.propTypes = {
  success: PropTypes.func.isRequired,
  back: PropTypes.func.isRequired,
  renderItem: PropTypes.func,
  footer: PropTypes.func,
  loading: PropTypes.bool,
  initialSelection: PropTypes.object,
  title: PropTypes.string.isRequired,
  fallbackText: PropTypes.string,
  dataSource: PropTypes.array,
  successText: PropTypes.string,
};

export default LinkModal;
