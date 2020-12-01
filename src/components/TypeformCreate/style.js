import styled from 'styled-components/macro';
import { Spin } from 'antd';

export const Spinner = styled(Spin)`
  margin: 30vh auto;
`;

export const Modal = styled.div`
  position: fixed;
  z-index: 100;
  top: 0;
  left: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100vw;
  height: 100vh;
  background: #fff9;
`;

export const ModalBox = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  max-width: 600px;
  width: 100vw;
  min-width: 45vw;
  height: 70vh;
  background: white;
  border-radius: 5px;
  box-shadow: 0 0 15px -5px #0005;
  transition: height 1s ease;
`;

export const ModalHeader = styled.div`
  background: #9edcb8;
  height: 35vh;
  border-bottom: 2px solid #eee;
`;

export const ModalTitle = styled.h1`
  font-weight: 800;
  padding: 10px 30px;
  margin-bottom: 0px;
`;

export const List = styled.div`
  display: flex;
  flex-direction: column;
  overflow: hidden;
  overflow-y: scroll;
`;

export const ListItem = styled.div`
  font-size: 1.3rem;
  cursor: pointer;
  border-top: 1px solid #eee;
  padding: 20px 30px;
  &:hover {
    background: ${({ active }) => (active ? '#529e72' : '#eee')};
  }
  background: ${({ active }) => active && '#9edcb8'};
  color: ${({ active }) => active && 'white'};
  display: flex;
  justify-content: space-between;
`;

export const ListItemTitle = styled.div`
  font-weight: 800;
  margin-right: 10px;
  align-items: baseline;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

export const ListItemId = styled.div`
  margin-right: 10px;
  align-self: flex-end;
`;

export const ListItemDate = styled.div`
  font-weight: 200;
  color: lighter();
  font-size: 1rem;
`;

export const ModalFooter = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 2px solid #eee;
  padding: 10px 20px;
`;

export const ActionsBtns = styled.div`
  display: flex;
  align-items: center;
`;

export const Selected = styled.div`
  display: flex;
  flex-direction: column;
  max-width: 45vw;
  width: 60%;
  min-width: 50%;
`;

export const SelectedInfo = styled.div`
  font-weight: 800;
  margin: 0 10px;
  font-size: 1.2rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

export const primaryColor = styled(SelectedInfo)`
  color: #9edcb8;
`;

export const TitleInput = styled.input`
  margin: 40px 40px;
  padding: 10px 10px;
  font-size: 1.2rem;
  font-weight: 800;
`;

export const ShortCodeInput = styled.input`
  margin: 40px 40px;
  padding: 10px 10px;
  font-size: 1.2rem;
  font-weight: 800;
`;

// TODO: fix the title length with '...' at the end
// TODO: styled components structure
// TODO: Set basic Style
