const InputSecret = () => (
  <>
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Enter client ID
      </label>
      <input
        type="text"
        className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
        placeholder="12345"
      ></input>
    </div>
    <div className="flex flex-col">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Enter client secret
      </label>
      <input
        type="text"
        className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
        placeholder="qwertyuiopsdfghjcvbn"
      ></input>
    </div>
  </>
);

export default InputSecret;
