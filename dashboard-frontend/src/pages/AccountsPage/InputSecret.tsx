import { ChangeEvent, useEffect, useState } from 'react';
import ConnectButton from '../../components/ConnectButton';
import { SecretAccountResource } from '../../types/account';

const InputSecret = ({
  account,
  slug,
}: {
  account: SecretAccountResource | null;
  slug: string;
}) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [dataSecret, setDataSecret] = useState<{
    client_id: string;
    client_secret: string;
    slug: string;
  }>({
    client_id: '',
    client_secret: '',
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
  }

  useEffect(() => {
    setDataSecret({
      client_id: account?.credentials?.clientId
        ? account?.credentials?.clientId
        : '',
      client_secret: account?.credentials?.clientSecret
        ? account?.credentials?.clientSecret
        : '',
      slug,
    });
  }, []);

  return (
    <>
      <div className="flex flex-col mb-4">
        <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
          Client ID
        </label>
        <input
          type="text"
          id="client_id"
          className="bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
          placeholder={
            account?.credentials
              ? account?.credentials?.clientId
              : 'Enter client ID'
          }
          onChange={e => handleChange(e)}
          disabled={loading}
        ></input>
      </div>
      <div className="flex flex-col mb-4">
        <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-300">
          Client secret
        </label>
        <input
          type="text"
          id="client_secret"
          className="placeholder-gray-500 bg-gray-100 rounded p-2 border focus:outline-none focus:border-blue-500"
          placeholder={
            account?.credentials
              ? account?.credentials?.clientSecret
              : 'Enter client secret'
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

export default InputSecret;
