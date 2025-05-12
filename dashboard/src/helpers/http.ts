/**
 * TODO: Add tests
 */

export const fetchWithTimeout = async (
  path: string,
  {
    timeout = 30000, // 30 seconds default timeout
    baseURL,
    ...requestInit
  }: { timeout?: number; baseURL?: string } & RequestInit
) => {
  const localHost = process.env.REACT_APP_SERVER_URL;
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  if (!baseURL) {
    baseURL = localHost;
  }

  const response = await fetch(`${baseURL}${path}`, {
    ...requestInit,
    signal: controller.signal,
  });

  clearTimeout(id);

  return response;
};
