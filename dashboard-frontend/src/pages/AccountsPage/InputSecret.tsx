import { SecretAccountResource } from '../../types/account';

const InputSecret = ({ account }: { account: SecretAccountResource }) => (
  <>
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Client ID
      </label>
      <input
        type="text"
        className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
        placeholder={account.credentials.clientId}
      ></input>
    </div>
    <div className="flex flex-col">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Client secret
      </label>
      <input
        type="text"
        className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
        placeholder={account.credentials.clientSecret}
      ></input>
    </div>
  </>
);

export default InputSecret;
