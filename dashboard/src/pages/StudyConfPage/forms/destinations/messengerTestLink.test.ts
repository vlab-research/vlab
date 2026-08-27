import { messengerTestLink, pageIdForDestination } from './messengerTestLink';
import { Creatives } from '../../../../types/conf';

describe('messengerTestLink', () => {
  it('builds an m.me link whose ref carries the shortcode under the `form` key', () => {
    // fly parses ?ref by splitting on '.' and pairing tokens (see utils.js:_group),
    // reading the `form` key. This asserts the exact shape a real ad click produces.
    expect(messengerTestLink('1004050362793638', 'sIcNrF10')).toBe(
      'https://m.me/1004050362793638?ref=form.sIcNrF10.vlabtest.1'
    );
  });

  it('returns undefined when the page id is missing (no creatives yet)', () => {
    expect(messengerTestLink(undefined, 'sIcNrF10')).toBeUndefined();
  });

  it('returns undefined when the shortcode is empty', () => {
    expect(messengerTestLink('1004050362793638', '')).toBeUndefined();
  });

  it('url-encodes an unusual shortcode so ref tokens survive the split', () => {
    expect(messengerTestLink('123', 'a b')).toBe(
      'https://m.me/123?ref=form.a%20b.vlabtest.1'
    );
  });
});

describe('pageIdForDestination', () => {
  const creatives = [
    {
      name: 'flier-5',
      destination: 'fly_messenger',
      template: { object_story_spec: { page_id: '111' }, actor_id: '111' },
      template_campaign: 'c1',
    },
    {
      name: 'other',
      destination: 'other_dest',
      template: { actor_id: '222' },
      template_campaign: 'c2',
    },
  ] as unknown as Creatives;

  it('matches a creative to the destination by name', () => {
    expect(pageIdForDestination(creatives, 'fly_messenger')).toBe('111');
  });

  it('falls back to actor_id when object_story_spec.page_id is absent', () => {
    expect(pageIdForDestination(creatives, 'other_dest')).toBe('222');
  });

  it('falls back to any creative page id when the name does not match', () => {
    expect(pageIdForDestination(creatives, 'unknown')).toBe('111');
  });

  it('returns undefined when there are no creatives', () => {
    expect(pageIdForDestination([], 'fly_messenger')).toBeUndefined();
    expect(pageIdForDestination(undefined, 'fly_messenger')).toBeUndefined();
  });
});
