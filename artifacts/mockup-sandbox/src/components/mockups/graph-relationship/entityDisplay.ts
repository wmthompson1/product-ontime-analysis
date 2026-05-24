export type EntityRecord = { table_name: string; qualified_name: string };
export type GroupedResults = Record<string, EntityRecord[]>;
export type SearchResult = { matches_found: number; grouped_results: GroupedResults };

/**
 * Returns the display string for the first entity in a SearchResult.
 * Format: "<table_name> (<source_key>)"
 *
 * Used to initialise selectedSource and selectedTarget so both always
 * derive from the same logic and stay in sync when MOCK_SEARCH_DATA changes.
 *
 * Returns an empty string when grouped_results has no entries or the first
 * group has no records.
 */
export function getFirstEntityDisplay(data: SearchResult): string {
  const firstSource = Object.keys(data.grouped_results)[0];
  if (!firstSource) return "";
  const firstRec = data.grouped_results[firstSource][0];
  if (!firstRec) return "";
  return `${firstRec.table_name} (${firstSource})`;
}
