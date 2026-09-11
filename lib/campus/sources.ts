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

export function sourceDates(source: Source) {
  return [
    source.publishedAt ? `发布：${source.publishedAt}` : '发布日期未注明',
    source.capturedAt ? `拍摄：${source.capturedAt}` : '拍摄日期未注明',
    source.retrievedAt ? `查阅：${source.retrievedAt}` : '',
  ]
    .filter(Boolean)
    .join(' · ');
}
