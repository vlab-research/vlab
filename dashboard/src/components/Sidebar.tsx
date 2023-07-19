import { matchPath, useLocation, Link, useParams } from 'react-router-dom';
import { classNames } from '../helpers/strings';

const Sidebar = ({ className = '' }: { className?: string }) => {
  const { pathname } = useLocation();
  const params = useParams<{ studySlug: string; conf: string }>();

  interface NavItem {
    name: string;
    href: string;
    current: boolean | undefined;
  }

  const navigation: NavItem[] = [
    {
      name: 'General',
      href: `/studies/${params.studySlug}/general`,
      current: matchPath(pathname, {
        path: `/studies/${params.studySlug}/general`,
        exact: true,
      })?.isExact,
    },
    {
      name: 'Recruitment',
      href: `/studies/${params.studySlug}/recruitment`,
      current: matchPath(pathname, {
        path: `/studies/${params.studySlug}/recruitment`,
        exact: true,
      })?.isExact,
    },
    {
      name: 'Destinations',
      href: `/studies/${params.studySlug}/destinations`,
      current: matchPath(pathname, {
        path: `/studies/${params.studySlug}/destinations`,
        exact: true,
      })?.isExact,
    },
    {
      name: 'Creatives',
      href: `/studies/${params.studySlug}/creatives`,
      current: matchPath(pathname, {
        path: `/studies/${params.studySlug}/creatives`,
        exact: true,
      })?.isExact,
    },
    {
      name: 'Audiences',
      href: `/studies/${params.studySlug}/audiences`,
      current: matchPath(pathname, {
        path: `/studies/${params.studySlug}/audiences`,
        exact: true,
      })?.isExact,
    },
    {
      name: 'Variables',
      href: `/studies/${params.studySlug}/variables`,
      current: matchPath(pathname, {
        path: `/studies/${params.studySlug}/variables`,
        exact: true,
      })?.isExact,
    },
    {
      name: 'Strata',
      href: `/studies/${params.studySlug}/strata`,
      current: matchPath(pathname, {
        path: `/studies/${params.studySlug}/strata`,
        exact: true,
      })?.isExact,
    },
  ];

  return (
    <nav
      data-testid="sidebar"
      className={classNames('bg-white shadow-sm', className)}
    >
      <div className="w-60 shadow-md bg-white px-2.5 absolute">
        {navigation.map((item: NavItem, i) => (
          <Link
            key={`${item.name}-${i}`}
            to={item.href}
            className={classNames(
              item.current
                ? 'border-l-4 border-indigo-500 text-gray-700 bg-gray-100 hover:text-gray-900'
                : 'border-transparent text-gray-500 hover:text-gray-900',
              'w-full	flex items-center text-l my-1 p-8 h-12 overflow-hidden font-medium text-ellipsis whitespace-nowrap rounded hover:bg-gray-100 transition duration-300 ease-in-out'
            )}
            aria-current={item.current ? 'page' : undefined}
          >
            {item.name}
          </Link>
        ))}
      </div>
    </nav>
  );
};

export default Sidebar;
