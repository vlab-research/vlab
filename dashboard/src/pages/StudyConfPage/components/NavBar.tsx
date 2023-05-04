import { createLabelFor } from '../../../helpers/strings';

const Navbar = ({
  formKeys,
  setIndex,
}: {
  formKeys: string[];
  setIndex: any;
}) => {
  const handleClick = (e: any, key: string) => {
    e.preventDefault();
    const newIndex = formKeys.indexOf(key);
    setIndex(() => newIndex);
  };

  return (
    <div className="w-60 h-full shadow-md bg-white px-1 absolute">
      <ul className="relative">
        {formKeys.map((key: string) => (
          <li className="relative" key={key}>
            <button
              className="w-full	flex items-center text-l mt-1 p-8 h-12 overflow-hidden font-medium text-gray-700 text-ellipsis whitespace-nowrap rounded hover:text-gray-900 hover:bg-gray-100 transition duration-300 ease-in-out focus:outline-none"
              onClick={e => handleClick(e, key)}
            >
              {createLabelFor(key)}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Navbar;
