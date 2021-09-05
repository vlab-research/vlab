import { useAuth0 as useRealAuth0 } from '@auth0/auth0-react';

const useAuth0 = (): Pick<
  ReturnType<typeof useRealAuth0>,
  | 'isAuthenticated'
  | 'isLoading'
  | 'user'
  | 'logout'
  | 'getAccessTokenSilently'
  | 'loginWithRedirect'
> => {
  const auth0Context = useRealAuth0();

  if (process.env.REACT_APP_RUNNING_IN_E2E_MODE) {
    return {
      isAuthenticated: true,
      isLoading: false,
      user: {
        name: 'testuser@vlab.digital',
        picture:
          'https://s.gravatar.com/avatar/862ea49e237479a3bb42efc8ed5dad4b?s=480&r=pg&d=https%3A%2F%2Fcdn.auth0.com%2Favatars%2Fte.png',
      },
      logout: () => {},
      getAccessTokenSilently: () =>
        Promise.resolve('e9005f1b-104e-4883-a8fb-3f3a72394260'),
      loginWithRedirect: () => Promise.resolve(),
    };
  }

  return auth0Context;
};

export default useAuth0;
