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
        type="text"
        id="client-id"
        className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
        placeholder={
          account?.credentials
            ? account?.credentials?.clientId
            : 'Enter client ID'
        }
      ></input>
    </div>
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Client secret
      </label>
      <input
        type="text"
        id="client-secret"
        className="placeholder-gray-500 bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
        placeholder={
          account?.credentials
            ? account?.credentials?.clientSecret
            : 'Enter client secret'
        }
      ></input>
    </div>
  </>
);

export default InputSecret;
