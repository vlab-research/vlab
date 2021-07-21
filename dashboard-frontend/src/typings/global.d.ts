interface Window {
  Cypress: unknown;
  handleFromCypress: (request: import('miragejs').Request) => Promise<{
    status: number;
    headers: Record<string, string>;
    body: Object;
  }>;
}
