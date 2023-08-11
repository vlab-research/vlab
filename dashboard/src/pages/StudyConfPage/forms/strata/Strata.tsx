import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { GenericTextInput, TextInputI } from '../../components/TextInput';
import { GenericMultiSelect, MultiSelectI } from '../../components/MultiSelect';
import PrimaryButton from '../../../../components/PrimaryButton';
import useCreateStudyConf from '../../hooks/useCreateStudyConf';
import { createStrataFromVariables } from '../../../../helpers/strata';
import { GlobalFormData, Stratum as StratumType } from '../../../../types/conf';

export interface FormData {
  id: string;
  quota: number;
}
const TextInput = GenericTextInput as TextInputI<FormData>;


const MultiSelect = GenericMultiSelect as MultiSelectI<StratumType>;

const Stratum: React.FC<{
  stratum: StratumType;
  creativeOptions: string[];
  onChange: (e: any) => void;
}> = ({ stratum, creativeOptions, onChange }) => {

  const handleMultiSelectChange = (selected: any[], name: string) => {
        onChange({target: {name, value: selected}})
  }  

  return (
    <>
      <TextInput
        name="id"
        type="text"
        value={stratum.id}
        disabled={true}
        placeholder="name"
        handleChange={onChange}
      />
      <TextInput
        name="quota"
        type="text"
        value={stratum.quota}
        placeholder="quota"
        handleChange={onChange}
      />
      <MultiSelect
        name="creatives"
        options={creativeOptions.map((c) => ({label: c, value: c}))} 
        handleMultiSelectChange={handleMultiSelectChange}
        value={stratum.creatives}
        label="Select which creatives to show to this stratum"
      ></MultiSelect>
      <div className="w-4/5 h-0.5 mr-8 my-6 rounded-md bg-gray-400"></div>
    </>
  );
};

interface Props {
  id: string;
  localData: StratumType[];
  globalData: GlobalFormData;
}
const Variables: React.FC<Props> = ({ globalData, id, localData }: Props) => {
  const { variables, creatives, audiences } = globalData;

  const params = useParams<{ studySlug: string }>();
  const studySlug = params.studySlug;

  const [formData, setFormData] = useState(localData || []);

  const regenerate = () => {
    const strata = createStrataFromVariables(variables, creatives, audiences);
    setFormData(strata);
  };

  const updateFormData = (e: any, index: number): void => {
    const clone = [...formData];
    const { name, value } = e.target;
    clone[index] = { ...clone[index], [name]: value };
    setFormData(clone);
  };

  const onSubmit = (e: any) => {
    e.preventDefault();

    // caste quotas
    const data = { [id]: formData.map(s => ({ ...s, quota: +s.quota })) };
    createStudyConf({ data, studySlug });
  };

  const { createStudyConf } = useCreateStudyConf(true, 'Strata saved');

  const allCreatives = creatives ? creatives.map((c: any) => c.name) : [];

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <div className="px-4 py-3 bg-gray-50 sm:px-6">
          <div className="sm:my-4">
            <div className="py-8 text-left">
              <PrimaryButton type="button" onClick={regenerate}>
                Generate from variables
              </PrimaryButton>
            </div>
            <form onSubmit={onSubmit}>
              <div className="mb-8">
                {formData.length === 0 ? (
                  <p> First create some variables! </p>
                ) : (
                  formData.map((s, i) => (
                    <Stratum
                      key={i}
                      stratum={s}
                      creativeOptions={allCreatives}
                      onChange={(e: any) => updateFormData(e, i)}
                    />
                  ))
                )}
              </div>

              <div className="p-6 text-right">
                <PrimaryButton type="submit" testId="form-submit-button">
                  Save
                </PrimaryButton>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Variables;
