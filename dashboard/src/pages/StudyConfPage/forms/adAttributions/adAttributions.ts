/**
 * Pure logic for the Ad Attributions step.
 * No React dependencies; testable in isolation.
 *
 * The mapping is one row per ad vlab created, frozen at creation with the
 * shortcode, creative name and stratum metadata that ad was published with. A
 * study whose destinations are in ref_mode "encoded" joins its survey export
 * against this on `ref_token`; the stratum columns then come back named as
 * they always were.
 */
import { AdAttributionsTable } from '../../../../types/study';

/** The header adopt's CSV writes the join key under. */
export const JOIN_COLUMN = 'ref_token';

const quote = (value: string): string =>
  /[",\n\r]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;

/**
 * The table as a CSV file.
 *
 * Rendered from the same rows the table shows rather than fetched separately,
 * so a file saved from this page and the page itself cannot show different
 * columns. adopt serves the identical bytes at
 * /{org}/studies/{slug}/ad-attributions.csv for a script doing the join.
 */
export const toCsv = (table: AdAttributionsTable): string =>
  [table.columns, ...table.rows.map(row => table.columns.map(c => row[c] ?? ''))]
    .map(cells => cells.map(quote).join(','))
    .join('\r\n') + '\r\n';

export const csvFilename = (studySlug: string): string =>
  `${studySlug}-ad-attributions.csv`;
