export interface ApiResponse<Data> {
  data: Data;
}

export interface PaginatedApiResponse<Data, PaginationExtraFields = void> {
  data: Data;
  pagination: {
    nextCursor: Cursor;
  } & PaginationExtraFields;
}

export type Cursor = string | null;
