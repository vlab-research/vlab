/**
 * TODO: Add tests
 */

const BASE = process.env.REACT_APP_SERVER_URL;

export const fetchWithTimeout = async (
  url: string,
  { timeout, ...requestInit }: { timeout: number } & RequestInit
) => {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  const response = await fetch(`${BASE}${url}`, {
    ...requestInit,
    signal: controller.signal,
  });

  clearTimeout(id);

  return response;
};
