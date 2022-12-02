import React from 'react';
import ListItem from '../../../components/ListItem';

const List = ({ ...props }: any) => {
  const { id, list } = props;
  const { label } = list;

  console.log(props);

  return (
    <React.Fragment>
      <div className="sm:my-4">
        {label && (
          <label
            htmlFor={id}
            className="block text-sm font-medium text-gray-700"
          >
            {label}
          </label>
        )}
        <ul className="flex flex-row items-center">
          list items here
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
        </ul>
      </div>
    </React.Fragment>
  );
};

export default List;
