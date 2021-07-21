export interface ApiListSucessResponse<Data> {
  data: Data[];
  pagination: {
    nextCursor: string | null;
  };
}
