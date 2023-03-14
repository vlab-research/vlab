import { createLabelFor } from '../helpers/strings';

const Navbar = ({
  configKeys,
  setIndex,
}: {
  configKeys: string[];
  setIndex: any;
}) => {
  const handleClick = (e: any, configKey: string) => {
    e.preventDefault();
    const newIndex = configKeys.indexOf(configKey);
    setIndex(() => newIndex);
  };

  return (
    <div className="w-60 h-full shadow-md bg-white px-1 absolute">
      <ul className="relative">
        {configKeys.map((configKey: string) => (
          <li className="relative" key={configKey}>
            <button
              className="w-full	flex items-center text-sm py-4 px-6 h-12 overflow-hidden text-gray-700 text-ellipsis whitespace-nowrap rounded hover:text-gray-900 hover:bg-gray-100 transition duration-300 ease-in-out"
              onClick={e => handleClick(e, configKey)}
            >
              {createLabelFor(configKey)}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Navbar;
