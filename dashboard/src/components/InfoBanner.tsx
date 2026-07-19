type Variant = 'info' | 'warning' | 'error';

type props = {
  message: string;
  variant?: Variant;
  action?: React.ReactNode;
  onDismiss?: () => void;
};

const variantStyles: Record<Variant, { box: string; icon: string; text: string }> = {
  info: {
    box: 'bg-blue-100 border-blue-500',
    icon: 'text-blue-500',
    text: 'text-blue-700',
  },
  warning: {
    box: 'bg-amber-100 border-amber-500',
    icon: 'text-amber-500',
    text: 'text-amber-700',
  },
  error: {
    box: 'bg-red-100 border-red-500',
    icon: 'text-red-500',
    text: 'text-red-700',
  },
};

export const InfoBanner: React.FC<props> = ({
  message,
  variant = 'info',
  action,
  onDismiss,
}) => {
  const styles = variantStyles[variant];

  return (
    <div className="flex">
      <div className={`p-5 w-full border-l-4 ${styles.box}`}>
        <div className="flex space-x-3 items-center">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            className={`flex-none fill-current h-4 w-4 ${styles.icon}`}
          >
            <path d="M12 0c-6.627 0-12 5.373-12 12s5.373 12 12 12 12-5.373 12-12-5.373-12-12-12zm-.001 5.75c.69 0 1.251.56 1.251 1.25s-.561 1.25-1.251 1.25-1.249-.56-1.249-1.25.559-1.25 1.249-1.25zm2.001 12.25h-4v-1c.484-.179 1-.201 1-.735v-4.467c0-.534-.516-.618-1-.797v-1h3v6.265c0 .535.517.558 1 .735v.999z" />
          </svg>
          <div className={`flex-1 leading-tight text-sm ${styles.text}`}>
            {message}
          </div>
          {action}
          {onDismiss && (
            <button
              type="button"
              aria-label="Dismiss"
              onClick={onDismiss}
              className={`flex-none text-lg leading-none px-1 ${styles.text} hover:opacity-60`}
            >
              ×
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
