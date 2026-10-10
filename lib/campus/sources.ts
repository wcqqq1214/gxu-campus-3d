export interface Source {
  id: string;
  name: string;
  url: string;
  publishedAt?: string | null;
  capturedAt?: string | null;
  retrievedAt?: string | null;
  note?: string;
}

/** One source registry serves data validation and the visible reference list. */
export function sourceIndex(sources: Source[]): Record<string, Source> {
  return Object.fromEntries(sources.map((source) => [source.id, source]));
}
