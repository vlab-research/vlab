import React, { useState } from 'react';
import PrimaryButton from '../../../../components/PrimaryButton';
import DeleteButton from '../../../../components/DeleteButton';
import AddButton from '../../../../components/AddButton';
import Variable from './Variable';
import { createLabelFor } from '../../../../helpers/strings';
import useAccounts from './useAccounts';
import useCampaigns from './useCampaigns';

interface Props {
  id: string;
  localData: any;
}

const Strata: React.FC<Props> = ({ id, localData }: Props) => {
  const initialState = [
    {
      name: '',
      id: '',
    },
  ];

  //TODO handle errorMessage
  const {account, errorMessage } = useAccounts()
  if (account == undefined) {
    // TODO: We should show an error message here
    // as none of the following logic will work without this
  }
  const [formData, setFormData] = useState<any[]>(
    localData ? localData : initialState
  );

  const updateFormData = (d: any, index: number): void => {
    const clone = [...formData];
    clone[index] = d;
    setFormData(clone);
  };

  const onSubmit = (e: any): void => {
    e.preventDefault();
  };

  const addVariable = (): void => {
    setFormData([...formData, ...initialState]);
  };

  const deleteDestination = (index: number): void => {
    const newArr = formData.filter((d: any, i: number) => index !== i);

    setFormData(newArr);
  };

  interface SelectProps {
    name: string;
    options: SelectOption[];
    value: string;
  }

  interface SelectOption {
    name: string;
    id: string;
  }

  const Select: React.FC<SelectProps> = ({ options, value }: SelectProps) => (
    <div className="sm:my-4">
      <label className="my-2 block text-sm font-medium text-gray-700">
        Pick a campaign template
      </label>
      <select
        className="w-4/5 mt-1 block shadow-sm sm:text-sm rounded-md"
        value={value}
      >
        {options.map((option: SelectOption, i: number) => (
          <option key={i} value={option.id}>
            {createLabelFor(option.name)}
          </option>
        ))}
      </select>
    </div>
  );

  const campaignsData = useCampaigns();

  const campaignsExist = campaignsData.campaigns.length > 0;

  const campaigns = [
    {
      name: 'vlab-vaping-pilot-2',
      id: '23849532279040149',
    },
    {
      name: 'Dante - Test',
      id: '23855338456650149',
    },
    {
      name: 'vlab-unicef-bebbo-v2-bulgaria-3',
      id: '23855151863270149',
    },
  ];

  return (
    <div className="md:grid md:grid-cols-3 md:gap-6">
      <div className="md:col-span-1">
        <div className="px-4 sm:px-0"></div>
      </div>
      <div className="mt-5 md:mt-0 md:col-span-2">
        <div className="px-4 py-3 bg-gray-50 sm:px-6">
          <div className="sm:my-4">
            <form onSubmit={onSubmit}>
              <div className="mb-8">
                <Select
                  name="campaign"
                  options={campaigns}
                  value={localData.id}
                ></Select>
                {formData.map((d: any, index: number) => {
                  return (
                    <>
                      <Variable
                        key={index}
                        data={d}
                        index={index}
                        updateFormData={updateFormData}
                      />
                      {formData.length > 1 && (
                        <div key={`${d.name}-${index}`}>
                          <div className="flex flex-row w-4/5 justify-between items-center mb-4">
                            <div className="w-full h-0.5 mr-8 rounded-md bg-gray-400"></div>
                            <DeleteButton
                              onClick={() => deleteDestination(index)}
                            ></DeleteButton>
                          </div>
                          <div />
                        </div>
                      )}
                    </>
                  );
                })}
                {formData.length === 1 && (
                  <div className="w-full h-0.5 mr-8 my-6 rounded-md bg-gray-400"></div>
                )}
                <div className="flex flex-row items-center">
                  <AddButton onClick={addVariable} />
                  <label className="ml-4 italic text-gray-700 text-sm">
                    Add a new variable
                  </label>
                </div>
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

export default Strata;
