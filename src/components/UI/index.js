import styled from 'styled-components/macro';
import { Link } from 'react-router-dom';

export const Container = styled.div`
  display: inline-block;
`;

export const CreateBtn = styled(Link)`
  margin: 10px;
  text-decoration: none;
  background-color: #262627;
  border: 0;
  border-radius: 2px;
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 600;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif,
    'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol';
  line-height: 24px;
  padding: 8px 16px;
  transition: 0.2s;
  white-space: nowrap;
  color: #fff;
  &:hover {
    color: #fff;
  }
`;

export const Button = styled.button`
  margin: 10px;
  text-decoration: none;
  border: 0;
  border-radius: 2px;
  color: #fff;
  display: inline-block;
  font-size: 0.9em;
  font-weight: 600;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif,
    'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol';
  line-height: 24px;
  padding: 12px 16px;
  transition: 0.2s;
  white-space: nowrap;
  flex: 1;
  cursor: pointer;
`;

export const PrimaryBtn = styled(Button)`
  background: #9edcb8;
  &:hover {
    background: #529e72;
  }
`;
export const SecondaryBtn = styled(Button)`
  background: #424242;
  &:hover {
    background: #222222;
  }
`;
