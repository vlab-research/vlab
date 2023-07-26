import React from 'react';
import { useForm, UseFormRegister, Path } from 'react-hook-form';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { RecruitmentDestination as FormData } from '../../../../types/conf';
import { Destination as DestinationType } from '../../../../types/conf';

const TextInput = GenericTextInput as TextInputI<FormData>;

interface Props {
  formData: FormData;
  updateFormData: (e: any) => void;
  destinations: DestinationType[];
}

interface SelectProps {
  name: Path<FormData>;
  options: SelectOption[];
  register: UseFormRegister<FormData>;
  label?: string;
  value: string;
}

interface SelectOption {
  name: string;
}

const Select: React.FC<SelectProps> = ({
  name,
  options,
  register,
  label,
}: SelectProps) => (
  <div className="sm:my-4">
    <label className="my-2 block text-sm font-medium text-gray-700">
      {label}
    </label>
    <select
      {...register(name)}
      className="w-4/5 mt-1 block shadow-sm sm:text-sm rounded-md"
    >
      {options.map((option: SelectOption, i: number) => (
        <option key={i} value={option.name}>
          {option.name}
        </option>
      ))}
    </select>
  </div>
);

const validateInput = (name: string, value: any) => {
  if (name === 'max_sample_per_arm' || name === 'budget_per_arm') {
    if (!value) {
      return parseInt('0');
    }
    return parseInt(value);
  } else return value;
};

const Destination: React.FC<Props> = ({
  formData,
  updateFormData,
  destinations,
}: Props) => {
  const { register } = useForm<FormData>({});

  const handleChange = (e: any) => {
    const { name, value } = e.target;
    updateFormData({ ...formData, [name]: validateInput(name, value) });
  };

  return (
    <>
      <Select
        name="destination"
        options={destinations}
        register={register}
        label="Choose a destination"
        value={formData.destination}
      ></Select>
      <TextInput
        name="ad_campaign_name_base"
        handleChange={handleChange}
        placeholder="E.g vlab-vaping-pilot-2"
        value={formData.ad_campaign_name_base}
      />
      <TextInput
        name="budget_per_arm"
        handleChange={handleChange}
        placeholder="E.g 8400"
        value={formData.budget_per_arm}
      />
      <TextInput
        name="max_sample_per_arm"
        handleChange={handleChange}
        placeholder="E.g 1000"
        value={formData.max_sample_per_arm}
      />
      <TextInput
        name="start_date"
        handleChange={handleChange}
        placeholder="E.g 2022-07-26T00:00:00"
        value={formData.start_date}
      />
      <TextInput
        name="end_date"
        handleChange={handleChange}
        placeholder="E.g 2022-08-05T00:00:00"
        value={formData.end_date}
      />
    </>
  );
};

export default Destination;
