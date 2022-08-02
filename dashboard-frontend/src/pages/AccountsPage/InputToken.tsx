import { TokenAccountResource } from '../../types/account';

const InputToken = ({ account }: { account: TokenAccountResource }) => (
  <>
    <div className="flex flex-col sm:mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Access token
      </label>
      <input
        type="text"
        className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
        placeholder={account.credentials.token}
      ></input>
    </div>
  </>
);

export default InputToken;
