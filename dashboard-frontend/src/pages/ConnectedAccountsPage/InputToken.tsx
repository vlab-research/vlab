const InputToken = () => (
  <>
    <div className="flex flex-col sm:mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Enter access token
      </label>
      <input
        type="text"
        className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
        placeholder="qwertyuiopsdfghjcvbn"
      ></input>
    </div>
  </>
);

export default InputToken;
