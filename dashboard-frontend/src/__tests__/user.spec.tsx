import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import * as moduleUseAuth0 from '../hooks/useAuth0';

jest.mock('@auth0/auth0-react', () => ({
  Auth0Provider: ({ children }: { children: React.ReactNode }) => children,
}));

describe('user', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('while the app is checking if the user is authenticated, a loader page is shown', () => {
    userAuthenticated(false, { isCheckingUserAuth: true });

    visit('/');

    screen.getByTestId('loading-page');
  });

  it('non authenticated user accessing studies page, is redirected to login page', () => {
    userAuthenticated(false);

    visit('/');

    screen.getByRole('button', { name: 'Log in' });
  });

  it('non authenticated user accessing a specific study page, is redirected to login page', () => {
    userAuthenticated(false);

    visit('/studies/weekly-consume-meat');

    screen.getByRole('button', { name: 'Log in' });
  });

  it('clicking the Log in button, starts the login flow', () => {
    const login = jest.fn();
    userAuthenticated(false, { login });
    visit('/login');

    screen.getByRole('button', { name: 'Log in' }).click();

    expect(login).toHaveBeenCalledTimes(1);
  });

  it('authenticated user accessing login page, are redirected to studies page', () => {
    userAuthenticated(true);

    visit('/login');

    screen.getByTestId('studies-page');
  });

  it('authenticated users can see their name/email and avatar in the header', () => {
    const user = {
      name: 'testuser',
      avatarUrl: 'https://s.img.com/avatar.png',
    };
    userAuthenticated(true, user);

    visit('/');

    const header = screen.getByTestId('header');
    expect(header).toContainElement(screen.getByText(user.name));
    const userAvatar = screen.getByTestId('user-avatar');
    expect(header).toContainElement(userAvatar);
    expect(userAvatar).toHaveAttribute('src', user.avatarUrl);
  });

  it('clicking user avatar opens a dropdown with a Sign out button', () => {
    userAuthenticated(true);
    visit('/');

    userEvent.click(screen.getByTestId('user-avatar'));

    screen.getByText('Sign out');
  });

  it('clicking the Sign out button, starts the logout flow', () => {
    const logout = jest.fn();
    userAuthenticated(true, { logout });
    visit('/');
    userEvent.click(screen.getByTestId('user-avatar'));

    userEvent.click(screen.getByText('Sign out'));

    expect(logout).toHaveBeenCalledTimes(1);
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
