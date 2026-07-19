import { matchPath, useLocation, Link, useParams } from 'react-router-dom';
import { classNames } from '../../../helpers/strings';
import { confs } from '../shared';
import useStudyErrors from '../hooks/useStudyErrors';

const Sidebar = ({ className = '' }: { className?: string }) => {
  const { pathname } = useLocation();
  const params = useParams<{ studySlug: string; conf: string }>();
  const { errors } = useStudyErrors(params.studySlug);

  interface NavItem {
    name: string;
    path: string;
    href: string;
    current: boolean | undefined;
  }

  const navigation: NavItem[] = confs.map(({ name, path }) => {
    return {
      name,
      path,
      href: `/studies/${params.studySlug}/${path}`,
      current: matchPath(pathname, {
        path: `/studies/${params.studySlug}/${path}`,
        exact: true,
      })?.isExact,
    }
  })

  // Draw the eye to the Errors tab when the study has open issues:
  // red for errors, amber for warnings-only.
  const hasErrors = errors.some(e => e.severity === 'error');
  const errorsDot = errors.length > 0
    ? hasErrors ? 'bg-red-500' : 'bg-amber-400'
    : null;

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
            {item.path === 'errors' && errorsDot && (
              <span
                data-testid="errors-tab-dot"
                className={classNames('ml-2 inline-block h-2 w-2 flex-none rounded-full', errorsDot)}
              />
            )}
          </Link>
        ))}
      </div>
    </nav>
  );
};

export default Sidebar;
