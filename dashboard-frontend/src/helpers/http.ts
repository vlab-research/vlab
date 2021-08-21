/**
 * TODO: Add tests
 */
export const fetchWithTimeout = async (
  requestInfo: RequestInfo,
  { timeout, ...requestInit }: { timeout: number } & RequestInit
) => {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  const response = await fetch(requestInfo, {
    ...requestInit,
    signal: controller.signal,
  });

  clearTimeout(id);

  return response;
};
