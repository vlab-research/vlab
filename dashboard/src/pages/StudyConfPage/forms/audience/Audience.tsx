import React from 'react';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { Audience as FormData } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  data: FormData;
  update: (e: any, index: number) => void;
  index: number;
}

const Audience: React.FC<Props> = ({ data, update, index }: Props) => {
  const handleChange = (e: any) => {
    const { name, value } = e.target;
    update({ ...data, [name]: value }, index);
  };

  return (
    <li>
      <TextInput
        name="name"
        handleChange={handleChange}
        placeholder="E.g Give your audience a name"
        value={data.name}
      />
      <div className="sm:my-4">
        <label className="my-2 block text-sm font-medium text-gray-700">
          Targeting
        </label>
        <div className="flex flex-col space-y-2">
          <label className="flex items-center space-x-2">
            <input
              type="radio"
              name={`audience-targeting-${index}`}
              checked={true}
              readOnly
              className="text-indigo-600"
            />
            <span className="text-sm text-gray-700">All respondents</span>
          </label>
          <label className="flex items-center space-x-2 opacity-50 cursor-not-allowed">
            <input
              type="radio"
              name={`audience-targeting-${index}`}
              disabled
              className="text-indigo-600"
            />
            <span className="text-sm text-gray-400">Selected respondents only</span>
            <span className="text-xs text-gray-400 italic">(not yet available)</span>
          </label>
        </div>
      </div>
    </li>
  );
};

export default Audience;
