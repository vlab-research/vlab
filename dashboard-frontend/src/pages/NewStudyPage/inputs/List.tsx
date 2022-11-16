import React, { useCallback, useState } from 'react';
import PrimaryButton from '../../../components/PrimaryButton';
import { PlusCircleIcon } from '@heroicons/react/solid';

const ListInput = ({
  config,
  setCurrentConfig,
  formData,
  setformData,
  ...props
}: any) => {
  const { id, label, options } = props;
  const { selector } = config;
  const [selectedOption, setSelectedOption] = useState({
    name: '',
    label: '',
  });

  const handleOnClick = (e: any) => {
    const { innerText } = e.target;
    const findOption = options.findIndex(
      (option: any) => option.label === innerText
    );
    const option = options[findOption];
    setSelectedOption(option);
  };

  const findNestedConfig = useCallback(() => {
    const index = options.findIndex(
      (option: any) => option.name === selectedOption.name
    );
    return selector?.options[index];
  }, [options, selectedOption, selector]);

  const addItem = () => {
    selector && setCurrentConfig(findNestedConfig());
  };

  return (
    <React.Fragment>
      <div className="sm:my-4">
        <ul className="flex flex-row items-center">
          {options &&
            options.map((option: any) => (
              <li
                key={option.label}
                className="w-auto text-center my-2 md:mr-2"
                role="presentation"
                onClick={handleOnClick}
              >
                <PrimaryButton
                  type="submit"
                  testId="new-destination-submit-button"
                >
                  {option.label}
                </PrimaryButton>
              </li>
            ))}
          <button onClick={addItem}>
            <div className="flex flex-row mx-2">
              <PlusCircleIcon
                className="mr-1.5 h-5 w-5 text-gray-400"
                aria-hidden="true"
              />
              {label && (
                <label
                  htmlFor={id}
                  className="block text-sm font-medium text-gray-700"
                >
                  {label}
                </label>
              )}
            </div>
          </button>
        </ul>
      </div>
    </React.Fragment>
  );
};

export default ListInput;
