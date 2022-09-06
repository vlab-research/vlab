import { classNames } from '../../helpers/strings';
import { TokenAccountResource } from '../../types/account';

const InputToken = ({
  account,
  index,
  errorMessage,
}: {
  account: TokenAccountResource | null;
  index: number;
  errorMessage?: string;
}) => (
  <>
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Token
      </label>
      <input
        data-testid={`input-token-${index}`}
        name="token"
        type="text"
        value={account?.credentials ? account?.credentials?.token : ''}
        placeholder={
          account?.credentials ? account?.credentials?.token : 'Enter token'
        }
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

export default InputToken;
