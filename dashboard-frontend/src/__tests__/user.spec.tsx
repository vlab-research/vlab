import { Response } from 'miragejs';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import * as moduleUseAuth0 from '../hooks/useAuth0';
import { authenticatedApiCalls } from '../helpers/api';
import { queryCache } from 'react-query';
import { makeServer } from '../server';

jest.mock('@auth0/auth0-react', () => ({
  Auth0Provider: ({ children }: { children: React.ReactNode }) => children,
}));

describe('user', () => {
  let server: ReturnType<typeof makeServer>;

  beforeEach(() => {
    server = makeServer({ environment: 'test' });
  });

  afterEach(() => {
    jest.restoreAllMocks();
    queryCache.clear();
    server.shutdown();
  });

  it('while the app is checking if the user is authenticated, a loader page is shown', () => {
    userAuthenticated(false, { isCheckingUserAuth: true });

    visit('/');

    screen.getByTestId('loading-page');
  });

  it('non authenticated user accessing studies page, is redirected to login page', () => {
    userAuthenticated(false);

    visit('/');

    screen.getByText('Ready to start?');
    screen.getByText('Log in now to view the progress of your Studies!');
    screen.getByRole('button', { name: 'Log in' });
  });

  it('non authenticated user accessing a specific study page, is redirected to login page', () => {
    userAuthenticated(false);

    visit('/studies/weekly-consume-meat');

    screen.getByText('Ready to start?');
    screen.getByText('Log in now to view the progress of your Studies!');
    screen.getByRole('button', { name: 'Log in' });
  });

  it('clicking the Log in button, starts the login flow', () => {
    const login = jest.fn();
    userAuthenticated(false, { login });
    visit('/login');

    screen.getByRole('button', { name: 'Log in' }).click();

    expect(login).toHaveBeenCalledTimes(1);
  });

  describe('when is authenticated', () => {
    it('the app tries to create the user in our backend, when it fails for a reason other than "user already exists", the login page with a generic error is shown', async () => {
      userAuthenticated(true);
      server.post('/users', () => new Response(500));

      visit('/');
      screen.getByTestId('loading-page');

      await waitFor(() => {
        screen.getByText('Oops, something went wrong!');
        screen.getByText(
          'Please check your internet connection and try again.'
        );
        screen.getByRole('button', { name: 'Log in' });
      });
    });

    it('the app tries to create the user in our backend, when the backend returns "user already exists" error, everything works as expected and the user can see the studies page', async () => {
      userAuthenticated(true);
      server.post('/users', () => new Response(422));

      visit('/');

      await waitFor(() => {
        screen.getByTestId('studies-page');
      });
    });

    it('and access the login page, is redirected to studies page', async () => {
      userAuthenticated(true);

      visit('/login');

      await waitFor(() => {
        screen.getByTestId('studies-page');
      });
    });

    it('can see their name/email and avatar in the header', async () => {
      const user = {
        name: 'testuser',
        avatarUrl: 'https://s.img.com/avatar.png',
      };
      userAuthenticated(true, user);

      visit('/');

      await waitFor(() => {
        const header = screen.getByTestId('header');
        expect(header).toContainElement(screen.getByText(user.name));
        const userAvatar = screen.getByTestId('user-avatar');
        expect(header).toContainElement(userAvatar);
        expect(userAvatar).toHaveAttribute('src', user.avatarUrl);
      });
    });

    it('clicking the avatar opens a dropdown with a Sign out button', async () => {
      userAuthenticated(true);
      visit('/');

      userEvent.click(await waitFor(() => screen.getByTestId('user-avatar')));

      screen.getByText('Sign out');
    });

    it('clicking the Sign out button, starts the logout flow', async () => {
      const logout = jest.fn();
      userAuthenticated(true, { logout });
      visit('/');
      userEvent.click(await waitFor(() => screen.getByTestId('user-avatar')));

      userEvent.click(screen.getByText('Sign out'));

      expect(logout).toHaveBeenCalledTimes(1);
    });
  });
});

const userAuthenticated = (
  isAuthenticated: boolean,
  options?: {
    isCheckingUserAuth?: boolean;
    name?: string;
    avatarUrl?: string;
    login?: () => Promise<void>;
    logout?: () => void;
  }
) => {
  jest.spyOn(moduleUseAuth0, 'default').mockImplementation(() => ({
    isAuthenticated,
    isLoading: options?.isCheckingUserAuth ?? false,
    user: {
      name: options?.name ?? 'testuser@vlab.digital',
      picture:
        options?.avatarUrl ??
        'https://s.gravatar.com/avatar/862ea49e237479a3bb42efc8ed5dad4b?s=480&r=pg&d=https%3A%2F%2Fcdn.auth0.com%2Favatars%2Fte.png',
    },
    logout: options?.logout ?? (() => {}),
    getAccessTokenSilently: () =>
      Promise.resolve('e9005f1b-104e-4883-a8fb-3f3a72394260'),
    loginWithRedirect: options?.login ?? (() => Promise.resolve()),
  }));
};

const visit = (path: string) => {
  window.history.pushState({}, 'Test page', path);
  return render(<App />);
};
