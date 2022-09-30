// config.js
import TextInput from './TextInput';
import Select from './Select';
import Dropdown from './Dropdown';

export const getConfig = ({ state, onChange }) => {
  return [
    {
      name: 'name',
      id: 'name',
      type: 'text',
      label: 'Name',
      component: TextInput,
      value: state['name'],
      onChange: onChange('name'),
    },
    {
      name: 'objective',
      id: 'objective',
      type: 'option',
      component: Select,
      label: 'Objective',
      value: state['objective'],
      onChange: onChange('objective'),
    },
    {
      name: 'optimizationGoal',
      id: 'optimizationGoal',
      type: 'option',
      component: Select,
      label: 'Optimization Goal',
      value: state['optimizationGoal'],
      onChange: onChange('optimizationGoal'),
    },
    {
      name: 'destinationType',
      id: 'destinationType',
      type: 'option',
      component: Select,
      label: 'Destination Type',
      value: state['destinationType'],
      onChange: onChange('destinationType'),
    },
    {
      name: 'minBudget',
      id: 'minBudget',
      type: 'text',
      component: TextInput,
      label: 'Minimum Budget',
      value: state['minBudget'],
      onChange: onChange('minBudget'),
    },
    {
      name: 'instagramId',
      id: 'instagramId',
      type: 'text',
      component: TextInput,
      label: 'Instagram ID',
      value: state['instagramId'],
      onChange: onChange('instagramId'),
    },
    {
      name: 'adAccount',
      id: 'adAccount',
      type: 'text',
      component: TextInput,
      label: 'Ad Account',
      value: state['adAccount'],
      onChange: onChange('adAccount'),
    },
    {
      name: 'country',
      id: 'country',
      type: 'country',
      component: Dropdown,
      label: 'Country',
      value: state['country'],
      onChange: onChange('country'),
    },
  ];
};
