import { Creatives } from '../../../../types/conf';

// Build an m.me "test your funnel" link for a Messenger (fly) destination.
//
// WHY THIS EXISTS: a Messenger destination routes an ad click into the fly bot,
// which starts a survey identified by `initial_shortcode`. If that shortcode does
// not resolve to a real form, the click lands in Messenger and dies silently — the
// user is never taken into the survey. This is exactly the class of failure that is
// invisible until you spend on ads and notice zero respondents (see
// planning/study-errors-surfacing.md). An m.me link lets the study owner click
// through the *real* funnel themselves, before spending a naira.
//
// FAITHFULNESS: this reproduces the production entry path exactly.
//  - A real ad's creative carries `url_tags=ref=<ref>` where the ref is built by
//    adopt/adopt/marketing.py:make_ref as `creative.<name>.form.<shortcode>...`.
//  - When the click opens Messenger, fly parses the referral ref in
//    fly/replybot/lib/typewheels/utils.js:getMetadata — it does `ref.split('.')`,
//    pairs adjacent tokens (`_group`), decodeURIComponent's each, and reads the
//    `form` key as the shortcode to load. Position does not matter; only that a
//    `form` key is present.
// So `?ref=form.<shortcode>` yields `{form: <shortcode>}` in the bot — the identical
// routing decision a real ad click makes. The `vlabtest` marker is inert in fly
// (getMetadata only cares about `form`) but tags the resulting conversation so these
// test runs are filterable from real response data downstream.
export function messengerTestLink(
  pageId: string | undefined,
  shortcode: string | undefined
): string | undefined {
  if (!pageId || !shortcode) return undefined;
  const ref = ['form', encodeURIComponent(shortcode), 'vlabtest', '1'].join('.');
  return `https://m.me/${pageId}?ref=${ref}`;
}

// The page a Messenger destination lands on is the Facebook page bound to its
// creatives (template.object_story_spec.page_id, equal to template.actor_id). A
// destination is matched to a creative by name (creative.destination === name). Fall
// back to any creative's page id, since a study normally uses a single page.
export function pageIdForDestination(
  creatives: Creatives | undefined,
  destinationName: string | undefined
): string | undefined {
  if (!creatives || creatives.length === 0) return undefined;

  const pageOf = (c: any): string | undefined =>
    c?.template?.object_story_spec?.page_id ?? c?.template?.actor_id;

  const matched = destinationName
    ? creatives.find(c => c.destination === destinationName)
    : undefined;

  return pageOf(matched) ?? creatives.map(pageOf).find(Boolean);
}
