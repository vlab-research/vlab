import { Fragment } from 'react';
import { matchPath, useLocation, Link } from 'react-router-dom';
import { Menu, Transition } from '@headlessui/react';
import { classNames } from '../helpers/strings';
import { ReactComponent as Logo } from '../assets/logo.svg';
import useAuth0 from '../hooks/useAuth0';

const Header = ({ className = '' }: { className?: string }) => {
  const { user } = useAuth0();

  return (
    <nav
      data-testid="header"
      className={classNames('bg-white shadow-sm', className)}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 justify-between">
          <div className="flex">
            <Logo className="h-8 self-center" title="Virtual Lab logo" />
            <Navbar />
          </div>

          <div className="flex items-center">
            <div className="text-gray-500 text-sm font-medium hidden sm:block">
              {user!.name}
            </div>
            <div className="ml-3">
              <UserAvatar />
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

const Navbar = () => {
  const { pathname } = useLocation();

  const navigation = [
    {
      name: 'Studies',
      href: '/',
      current: matchPath(pathname, {
        path: '/',
        exact: true,
      })?.isExact,
    },
  ];

  return (
    <div className="-my-px ml-6 flex space-x-8">
      {navigation.map(item => (
        <Link
          key={item.name}
          to={item.href}
          className={classNames(
            item.current
              ? 'border-indigo-500 text-gray-900'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            'inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium'
          )}
          aria-current={item.current ? 'page' : undefined}
        >
          {item.name}
        </Link>
      ))}
    </div>
  );
};

const UserAvatar = () => {
  const { user, logout } = useAuth0();

  return (
    <Menu as="div" className="relative">
      <div>
        <Menu.Button className="bg-white rounded-full flex text-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
          <span className="sr-only">Open user menu</span>
          <img
            data-testid="user-avatar"
            className="h-8 w-8 rounded-full"
            src={user!.picture}
            alt=""
          />
        </Menu.Button>
      </div>
      <Transition
        as={Fragment}
        enter="transition ease-out duration-200"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <Menu.Items className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg py-1 bg-white ring-1 ring-black ring-opacity-5 focus:outline-none">
          <Menu.Item>
            {({ active }) => (
              <div
                onClick={() => logout({ returnTo: window.location.origin })}
                role="button"
                className={classNames(
                  active ? 'bg-gray-100' : '',
                  'block px-4 py-2 text-sm text-gray-700 cursor-pointer'
                )}
              >
                Sign out
              </div>
            )}
          </Menu.Item>
        </Menu.Items>
      </Transition>
    </Menu>
  );
};

export default Header;
