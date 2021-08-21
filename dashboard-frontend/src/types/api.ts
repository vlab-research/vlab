export interface ApiResponse<Data> {
  data: Data;
  pagination: {
    nextCursor: Cursor;
  };
}

export interface PaginatedApiResponse<Data, PaginationExtraFields = void> {
  data: Data;
  pagination: {
    nextCursor: Cursor;
  } & PaginationExtraFields;
}

export type Cursor = string | null;
