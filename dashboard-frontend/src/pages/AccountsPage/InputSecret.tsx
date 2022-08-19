import { SecretAccountResource } from '../../types/account';

const InputSecret = ({
  account,
}: {
  account: SecretAccountResource | null;
}) => (
  <>
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Client ID
      </label>
      <input
        data-testid="input-client-id"
        type="text"
        className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
        value={account?.credentials ? account?.credentials?.clientId : ''}
        placeholder="Enter client ID"
      ></input>
    </div>
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Client secret
      </label>
      <input
        data-testid="input-client-secret"
        type="text"
        className="placeholder-gray-500 bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
        value={account?.credentials ? account?.credentials?.clientSecret : ''}
        placeholder="Enter client secret"
      ></input>
    </div>
  </>
);

export default InputSecret;
