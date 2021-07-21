import { classNames } from '../helpers/strings';
import { ReactComponent as Logo } from '../assets/logo.svg';

const Header = ({ className = '' }: { className?: string }) => (
  <nav className={classNames('bg-white shadow-sm', className)}>
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="flex h-16">
        <Logo className="h-8 self-center" title="Virtual Lab logo" />
        <Navbar />
      </div>
    </div>
  </nav>
);

const Navbar = () => {
  const navigation = [{ name: 'Studies', href: '#', current: true }];

  return (
    <div className="-my-px ml-6 flex space-x-8">
      {navigation.map(item => (
        <a
          key={item.name}
          href={item.href}
          className={classNames(
            item.current
              ? 'border-indigo-500 text-gray-900'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            'inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium'
          )}
          aria-current={item.current ? 'page' : undefined}
        >
          {item.name}
        </a>
      ))}
    </div>
  );
};

export default Header;
