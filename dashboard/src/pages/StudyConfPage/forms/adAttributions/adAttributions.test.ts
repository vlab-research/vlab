import { JOIN_COLUMN, csvFilename, toCsv } from './adAttributions';

const table = {
  columns: ['ad_id', 'network', 'ref_token', 'gender', 'created'],
  rows: [
    {
      ad_id: 'ad-1',
      network: 'facebook',
      ref_token: 'a1b2c3d4e5',
      gender: 'women',
      created: '2026-08-16T00:00:00+00:00',
    },
  ],
};

describe('toCsv', () => {
  it('writes the table it was given, header first', () => {
    // Rendered from the rows the table shows rather than fetched separately,
    // so a file saved from the page and the page itself cannot disagree.
    const lines = toCsv(table).trim().split('\r\n');

    expect(lines[0]).toBe('ad_id,network,ref_token,gender,created');
    expect(lines[1]).toBe(
      'ad-1,facebook,a1b2c3d4e5,women,2026-08-16T00:00:00+00:00'
    );
  });

  it('joins on the key swoosh joins on', () => {
    expect(table.columns).toContain(JOIN_COLUMN);
  });

  it('quotes a value that would otherwise break the row', () => {
    const csv = toCsv({
      columns: ['ad_id', 'creative'],
      rows: [{ ad_id: 'ad-1', creative: 'Smiling, "Static"' }],
    });

    expect(csv.trim().split('\r\n')[1]).toBe('ad-1,"Smiling, ""Static"""');
  });

  it('leaves a cell a row does not have empty', () => {
    // Columns are a union across rows, so a study whose stratum conf changed
    // mid-flight has rows frozen under two shapes and both survive.
    const csv = toCsv({
      columns: ['ad_id', 'Age'],
      rows: [{ ad_id: 'ad-1' }, { ad_id: 'ad-2', Age: 'old' }],
    });

    expect(csv.trim().split('\r\n').slice(1)).toEqual(['ad-1,', 'ad-2,old']);
  });

  it('still names the columns for a study with no ads', () => {
    expect(toCsv({ columns: ['ad_id', 'network'], rows: [] }).trim()).toBe(
      'ad_id,network'
    );
  });
});

describe('csvFilename', () => {
  it('names the file after the study', () => {
    expect(csvFilename('mnch-week')).toBe('mnch-week-ad-attributions.csv');
  });
});
