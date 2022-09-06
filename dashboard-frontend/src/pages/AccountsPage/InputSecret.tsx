import { classNames } from '../../helpers/strings';
import { SecretAccountResource } from '../../types/account';

const InputSecret = ({
  account,
  index,
  errorMessage,
}: {
  account: SecretAccountResource | null;
  index: number;
  errorMessage?: string;
}) => (
  <>
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Client ID
      </label>
      <input
        data-testid={`input-client-id-${index}`}
        id="client-id"
        name="client-id"
        type="text"
        value={account?.credentials ? account?.credentials?.clientId : ''}
        placeholder="Enter client ID"
        onChange={event => event.target.value}
        className={classNames(
          'mt-1 block w-full shadow-sm sm:text-sm rounded-md',
          errorMessage
            ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
            : 'focus:ring-indigo-500 focus:border-indigo-500  border-gray-300'
        )}
      ></input>
    </div>
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Client secret
      </label>
      <input
        data-testid={`input-client-secret-${index}`}
        name="client-secret"
        type="text"
        value={account?.credentials ? account?.credentials?.clientSecret : ''}
        placeholder="Enter client secret"
        onChange={event => event.target.value}
        className={classNames(
          'mt-1 block w-full shadow-sm sm:text-sm rounded-md',
          errorMessage
            ? 'focus:ring-red-500 focus:border-red-500 border-red-300 text-red-900 pr-10'
            : 'focus:ring-indigo-500 focus:border-indigo-500  border-gray-300'
        )}
      ></input>
    </div>
  </>
);

export default InputSecret;
