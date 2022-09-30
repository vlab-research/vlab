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
      name: 'optimization_goal',
      id: 'optimization_goal',
      type: 'option',
      component: Select,
      label: 'Optimization Goal',
      value: state['optimization_goal'],
      onChange: onChange('optimization_goal'),
    },
    {
      name: 'destination_type',
      id: 'destination_type',
      type: 'option',
      component: Select,
      label: 'Destination Type',
      value: state['destination_typel'],
      onChange: onChange('destination_type'),
    },
    {
      name: 'min_budget',
      id: 'min_budget',
      type: 'text',
      component: TextInput,
      label: 'Minimum Budget',
      value: state['min_budget'],
      onChange: onChange('min_budget'),
    },
    {
      name: 'instagram_id',
      id: 'instagram_id',
      type: 'text',
      component: TextInput,
      label: 'Instagram ID',
      value: state['instagram_id'],
      onChange: onChange('instagram_id'),
    },
    {
      name: 'ad_account',
      id: 'ad_account',
      type: 'text',
      component: TextInput,
      label: 'Ad Account',
      value: state['ad_account'],
      onChange: onChange('ad_account'),
    },
    {
      name: 'country_code',
      id: 'country_code',
      type: 'countryCode',
      component: Dropdown,
      label: 'Country',
      value: state['country_code'],
      onChange: onChange('country_code'),
    },
  ];
};
