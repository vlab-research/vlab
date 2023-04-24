import { useRef, useCallback } from 'react';

const useInfiniteScrolling = ({
  isLoading,
  canFetchMore,
  fetchMore,
}: {
  isLoading: boolean;
  canFetchMore: boolean;
  fetchMore: () => void;
}) => {
  const observer = useRef<InstanceType<typeof IntersectionObserver>>();

  const lastElementRef = useCallback(
    node => {
      if (isLoading) {
        return;
      }

      if (observer.current) {
        observer.current.disconnect();
      }

      observer.current = new IntersectionObserver(entries => {
        if (entries[0].isIntersecting && canFetchMore) {
          fetchMore();
        }
      });

      if (node) {
        observer.current.observe(node);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isLoading, canFetchMore]
  );

  return {
    lastElementRef,
  };
};

export default useInfiniteScrolling;
