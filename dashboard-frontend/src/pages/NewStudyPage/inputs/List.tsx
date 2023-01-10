import { Fragment } from 'react';
import ListItem from '../../../components/ListItem';
import { PlusCircleIcon } from '@heroicons/react/solid';
import { createNameFor } from '../../../helpers/strings';
import { addOne } from '../../../helpers/numbers';

const List = ({ setCount, savedForms, list_label, call_to_action }: any) => {
  const handleClick = () => {
    setCount((prevCount: number) => addOne(prevCount));
  };

  return (
    <Fragment>
      <div className="sm:my-4">
        {list_label && (
          <label
            htmlFor={createNameFor(list_label)}
            className="text-sm font-medium text-gray-700 mb-2"
          >
            {list_label}
          </label>
        )}
        <ul className="flex flex-row items-center">
          {savedForms &&
            savedForms.map((val: any) => (
              <ListItem
                testId="list-item"
                key={val}
                className="w-auto text-center my-2 md:mr-2"
              >
                {val}
              </ListItem>
            ))}
          {call_to_action && (
            <button
              className="flex flex-row items-center"
              onClick={e => handleClick()}
            >
              <PlusCircleIcon
                className="mr-1.5 h-5 w-5 text-gray-400"
                aria-hidden="true"
              ></PlusCircleIcon>
              <span className="block text-sm font-medium text-gray-700">
                {call_to_action}
              </span>
            </button>
          )}
        </ul>
      </div>
    </Fragment>
  );
};

export default List;
