import { Fragment } from 'react';
// import ListItem from '../../../components/ListItem';
import { PlusCircleIcon } from '@heroicons/react/solid';

const List = ({ formData, setFormData, ...props }: any) => {
  const { label, id, calltoaction } = props;

  const handleClick = () => {};

  // const savedValues = [1, 2, 3];

  return (
    <Fragment>
      <div className="sm:my-4">
        {label && (
          <label
            htmlFor={id}
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            {label}
          </label>
        )}
        <ul className="flex flex-row items-center">
          {/* {savedValues &&
            savedValues.map((val: any) => (
              <ListItem
                testId="list-item"
                key={val}
                className="w-auto text-center my-2 md:mr-2"
              >
                {val}
              </ListItem>
            ))} */}

          {calltoaction && (
            <button
              className="flex flex-row items-center"
              onClick={() => handleClick()}
            >
              <PlusCircleIcon
                className="mr-1.5 h-5 w-5 text-gray-400"
                aria-hidden="true"
              ></PlusCircleIcon>
              <span className="block text-sm font-medium text-gray-700">
                {calltoaction}
              </span>
            </button>
          )}
        </ul>
      </div>
    </Fragment>
  );
};

export default List;
