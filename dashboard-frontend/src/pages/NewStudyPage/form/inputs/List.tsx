import { Fragment } from 'react';
import { PlusCircleIcon } from '@heroicons/react/solid';
import { addOne } from '../../../../helpers/numbers';

const List = (props: any) => {
  const { config, setCount } = props;
  const { call_to_action } = config;

  const handleClick = () => {
    setCount((prevCount: number) => addOne(prevCount));
  };

  return (
    <Fragment>
      <div className="flex justify-center p-2 sm:my-4">
        <button className="flex flex-row items-center" onClick={handleClick}>
          <PlusCircleIcon
            className="mr-1.5 h-5 w-5 text-gray-400"
            aria-hidden="true"
          ></PlusCircleIcon>
          <span className="block text-sm font-medium text-gray-700">
            {call_to_action}
          </span>
        </button>
      </div>
    </Fragment>
  );
};

export default List;
