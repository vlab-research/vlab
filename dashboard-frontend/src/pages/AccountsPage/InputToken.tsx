import { TokenAccountResource } from '../../types/account';

const InputToken = ({ account }: { account: TokenAccountResource | null }) => (
  <>
    <div className="flex flex-col mb-4">
      <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
        Token
      </label>
      <input
        type="text"
        id="token"
        className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
        placeholder={
          account?.credentials ? account?.credentials?.token : 'Enter token'
        }
      ></input>
    </div>
  </>
);

export default InputToken;
