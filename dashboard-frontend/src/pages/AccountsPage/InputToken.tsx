import { TokenAccountResource } from '../../types/account';

const InputToken = ({
  account,
  index,
  setFormData,
}: {
  account: TokenAccountResource | null;
  index: number;
  setFormData: any;
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
        className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
        value={account?.credentials ? account?.credentials?.token : ''}
        placeholder={
          account?.credentials ? account?.credentials?.token : 'Enter token'
        }
        onChange={event => setFormData(event.target.value)}
      ></input>
    </div>
  </>
);

export default InputToken;
