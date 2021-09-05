import useAuth0 from '../hooks/useAuth0';
import { authenticatedApiCalls as apiCalls } from '../helpers/api';

const useAuthenticatedApi = () => {
  const { getAccessTokenSilently } = useAuth0();

  type AuthenticatedApiCalls = {
    [Property in keyof typeof apiCalls]: (
      params: Omit<Parameters<typeof apiCalls[Property]>[0], 'accessToken'>
    ) => ReturnType<typeof apiCalls[Property]>;
  };

  const apiCallNames: Array<keyof typeof apiCalls> = Object.keys(
    apiCalls
  ) as any;

  const calls: AuthenticatedApiCalls = apiCallNames.reduce(
    (acc, apiCallName) => {
      acc[apiCallName] = async (params: any) =>
        apiCalls[apiCallName]({
          ...params,
          accessToken: await getAccessTokenSilently(),
        });

      return acc;
    },
    {} as any
  ) as any;

  return calls;
};

export default useAuthenticatedApi;
