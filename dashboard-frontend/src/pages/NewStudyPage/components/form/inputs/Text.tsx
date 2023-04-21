import { classNames } from '../../../../../helpers/strings';

const Text = ({ onChange, ...props }: any) => {
  const { id, name, label, helper_text, value, error } = props;

  const eventHandler = (e: any) => {
    onChange({ type: e.type, value: e.target.value });
  };

  return (
    <div className="sm:my-4">
      {label && (
        <label
          htmlFor={id}
          className="block mb-1 text-sm font-medium text-gray-700"
        >
          {label}
        </label>
      )}
      <div className="relative">
        <input
          {...props}
          id={id}
          name={name}
          value={value}
          required
          placeholder={helper_text}
          onChange={eventHandler}
          data-testid={`${id}-${name}-input`}
          className={classNames(
            'block w-4/5 shadow-sm sm:text-sm rounded-md',
            error
              ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
              : 'focus:ring-indigo-500 focus:border-indigo-500 border-gray-300'
          )}
        />
      </div>
    </div>
  );
};

export default Text;
