import { Fragment } from 'react';
import ListItem from '../../../components/ListItem';
import { PlusCircleIcon } from '@heroicons/react/solid';

const List = ({ ...props }: any) => {
  const { label, id, callToAction } = props;

  const arr = [1, 2];

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
          {arr.map(() => {
            return <ListItem className="mr-2">list item</ListItem>;
          })}
          {/* {selectedOptions &&
            selectedOptions.map((option: any) => (
              <ListItem
                testId="list-item"
                key={option.label}
                className="w-auto text-center my-2 md:mr-2"
              >
                {option.label}
              </ListItem>
            ))} */}
          {callToAction && (
            <button className="flex flex-row items-center">
              <PlusCircleIcon
                className="mr-1.5 h-5 w-5 text-gray-400"
                aria-hidden="true"
              ></PlusCircleIcon>
              <span className="block text-sm font-medium text-gray-700">
                {callToAction}
              </span>
            </button>
          )}
        </ul>
      </div>
    </Fragment>
  );
};

export default List;
