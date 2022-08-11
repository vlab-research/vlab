import { ChangeEvent, useEffect, useState } from 'react';
import ConnectButton from '../../components/ConnectButton';
import { TokenAccountResource } from '../../types/account';

const InputToken = ({
  account,
  slug,
}: {
  account: TokenAccountResource | null;
  slug: string;
}) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [dataSecret, setDataSecret] = useState<{
    token: string;
    slug: string;
  }>({
    token: '',
    slug,
  });

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const { id, value } = e.target;
    setDataSecret(prevState => ({
      ...prevState,
      [id]: value,
    }));
  }

  function handleConnect() {
    setLoading(true);
    console.log('save data secret', dataSecret);
    setLoading(false);
  }

  useEffect(() => {
    setDataSecret({
      token: account?.credentials?.token ? account?.credentials?.token : '',
      slug,
    });
  }, []);

  return (
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
          onChange={e => handleChange(e)}
          disabled={loading}
        ></input>
      </div>
      {account?.credentials ? (
        <ConnectButton buttonLabel="Update" onClick={handleConnect} disabled={loading} />
      ) : (
        <ConnectButton buttonLabel="Connect" onClick={handleConnect} disabled={loading} />
      )}
    </>
  );
};

export default InputToken;
