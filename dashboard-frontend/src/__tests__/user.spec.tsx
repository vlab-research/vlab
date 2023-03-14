import { Response } from 'miragejs';
import { render, act, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { authenticatedApiCalls } from '../helpers/api';
import { queryCache } from 'react-query';
import { makeServer } from '../server';
import { useAuth0 } from '@auth0/auth0-react';
const mockUser = {
      isLoading: false,
      user: { sub: "foobar" },
      isAuthenticated: true,
      loginWithRedirect: jest.fn(),
      logout: jest.fn(),
      getAccessTokenSilently:  () =>
      Promise.resolve('e9005f1b-104e-4883-a8fb-3f3a72394260'),
}

jest.mock('@auth0/auth0-react', () => ({
  Auth0Provider: ({ children }: { children: React.ReactNode }) => children,
  withAuthenticationRequired: ((component, _) => component),
  useAuth0: () => {
    return mockUser
  }
}));

describe('user', () => {
  let server: ReturnType<typeof makeServer>;

  beforeEach(() => {
    server = makeServer({environment: "test"});
  });

  afterEach(() => {
    jest.restoreAllMocks();
    queryCache.clear();
    server.shutdown();
  });

  it('while the app is checking if the user is authenticated, a loader page is shown', () => {
    act(() => {
      mockUser.isLoading = true
      visit('/');
      screen.getByTestId('loading-page');
    });
  });

  it('non authenticated user accessing studies page, is redirected to login page', () => {
      mockUser.isLoading = false
      mockUser.isAuthenticated = false
      visit('/');
      screen.getByText('Ready to start?');
      screen.getByText('Log in now to view the progress of your Studies!');
      screen.getByRole('button', { name: 'Log in' });
  });

  it('non authenticated user accessing a specific study page, is redirected to login page', () => {
    mockUser.isLoading = false
    mockUser.isAuthenticated = false
    visit('/studies/weekly-consume-meat');
    screen.getByText('Ready to start?');
    screen.getByText('Log in now to view the progress of your Studies!');
    screen.getByRole('button', { name: 'Log in' });
  });

  it('clicking the Log in button, starts the login flow', () => {
    visit('/login');
    const LoginBtn = screen.getByRole('button', { name: 'Log in' });
    fireEvent.click(LoginBtn)
    expect(mockUser.loginWithRedirect).toHaveBeenCalled();
  });

  describe('when is authenticated', () => {
    it('the app tries to create the user in our backend, when it fails for a reason other than "user already exists", the login page with a generic error is shown', async () => {
      server.post('/users', () => new Response(500));
      mockUser.isLoading = false
      mockUser.isAuthenticated = true
      visit('/');
      await waitFor(() => {
        screen.getByText('Oops, something went wrong!');
        screen.getByText(
          'Please check your internet connection and try again.'
        );
        screen.getByRole('button', { name: 'Log in' });
      });
    });

    it('the app tries to create the user in our backend, when the backend returns "user already exists" error, everything works as expected and the user can see the studies page', async () => {
      mockUser.isLoading = false
      mockUser.isAuthenticated = true
      server.post('/users', () => new Response(422));

      visit('/');
      await waitFor(() => {
        screen.getByTestId('studies-page');
      });
    });
    it('and access the login page, is redirected to studies page', async () => {

      mockUser.isLoading = false
      mockUser.isAuthenticated = true
      visit('/login');
      await waitFor(() => {
        screen.getByTestId('studies-page');
      })
    });

    it('can see their name/email and avatar in the header', async () => {
      const user = {
        name: 'testuser',
        picture: 'https://s.img.com/avatar.png',
      };
      mockUser.isLoading = false
      mockUser.isAuthenticated = true
      mockUser.user = user
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
      mockUser.isLoading = false
      mockUser.isAuthenticated = true
      visit('/');

      userEvent.click(await waitFor(() => screen.getByTestId('user-avatar')));

      screen.getByText('Sign out');
    });

    it('clicking the Sign out button, starts the logout flow', async () => {
      mockUser.isLoading = false
      mockUser.isAuthenticated = true
      visit('/');
      userEvent.click(await waitFor(() => screen.getByTestId('user-avatar')));

      userEvent.click(screen.getByText('Sign out'));

      expect(mockUser.logout).toHaveBeenCalledTimes(1);
    });
  });
});

const visit = (path: string) => {
    window.history.pushState({}, 'Test page', path);
    return render(<App />);
};
