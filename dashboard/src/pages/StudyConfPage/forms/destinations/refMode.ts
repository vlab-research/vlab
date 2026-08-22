/**
 * Pure logic for how a destination's ads carry attribution.
 *
 * A recruitment ad carries a **ref** — the string Meta returns to fly on a
 * click. How much the ref carries, and how attribution is recovered from it, is
 * the destination's `ref_mode`. The researcher never wants a `ref_mode`; they
 * want, at most, two things:
 *
 *   1. attribute respondents to the stratum that recruited them, and
 *   2. not show the respondent an ugly, editable tracking string.
 *
 * Everything else is mechanism. So this module models the task and frames each
 * option by what it does to the researcher's data — see refModeConsequence. The
 * word `ref_mode` is never shown, and neither is "encoded" as jargon.
 *
 * Two modes are offered:
 *
 *   encoded    `r.<token>` — clean AND attributes, via the ad_attributions
 *              join on ref_token. The default, on every channel.
 *   thick      `creative.X.gender.women.form.Y` — everything inline, no DB.
 *              Correct and free on Messenger (the ref is invisible there), so
 *              it stays available as the legacy-but-useful path.
 *
 * A third mode, "shortcode" (thin — clean ref that attributes nobody), exists
 * in the model and is deliberately NOT offered here. It was only ever the
 * WhatsApp/multi default, and a destination-type census found no production
 * population on those channels: 892 messenger, 11 web, 3 website, 0 whatsapp,
 * 0 multi. So there is no stored conf to preserve, and making the footgun
 * unreachable beats discouraging it. It is still resolvable — an old conf with
 * `ref_mode` absent and `include_metadata_in_ref` false resolves to it — which
 * is why displayedRefMode can return it and refModeOptions can surface it as a
 * disabled current value. Unreachable from the form is what "removed" means.
 *
 * See planning/ref-mode-dashboard-ux.md and documentation/ad-attributions.md.
 */
import { Destination, RefMode } from '../../../../types/conf';

export const REF_MODE_ENCODED = 'encoded';

/**
 * Thick's stored name is "metadata" — it says what the ref carries, which is
 * the whole stratum metadata. Named as a constant because the string is a
 * contract with adopt's RefMode literal, not a label; the label is in
 * refModeLabel.
 */
export const REF_MODE_THICK = 'metadata';

/** Thin. Never offered; see the module comment. */
export const REF_MODE_THIN = 'shortcode';

export const MESSENGER = 'messenger';

/**
 * The destination types that carry a ref mode at all.
 *
 * Web and app destinations are deliberately absent: neither has an
 * `initial_shortcode`, because their url_template / deeplink_template already
 * points at a specific survey. Routing is not a job the ref does for them, so
 * there is no mode to choose.
 */
export const REF_MODE_DESTINATION_TYPES = [MESSENGER, 'whatsapp', 'multi'];

export const carriesRefMode = (destinationType: string): boolean =>
  REF_MODE_DESTINATION_TYPES.includes(destinationType);

/**
 * Whether every fly destination in the study is Messenger.
 *
 * Thick is offered on pure-Messenger studies only. Its one cost — a visible,
 * editable ref sitting in the respondent's compose box — lands entirely on the
 * WhatsApp arm, so offering it on a study that has any WhatsApp or multi
 * destination would reintroduce the per-channel heterogeneity the encoded
 * default exists to remove: a multi-channel study would attribute two different
 * ways, and the researcher would join their data two different ways depending
 * on which arm a respondent arrived through. That confusion surfaces at
 * analysis time, months later, to someone who was not in the room.
 *
 * Judged across the whole destination list rather than per destination, which
 * is why this takes the study's destinations and not just one.
 */
export const isPureMessengerStudy = (destinations: Destination[]): boolean => {
  const flyDestinations = destinations
    .map(d => (d as { type?: string }).type || '')
    .filter(carriesRefMode);

  return flyDestinations.length > 0 && flyDestinations.every(t => t === MESSENGER);
};

export const refModeLabel = (mode: string): string => {
  switch (mode) {
    case REF_MODE_ENCODED:
      return 'Clean link — look the stratum up afterwards';
    case REF_MODE_THICK:
      return 'Stratum values inline in the link (Messenger only)';
    case REF_MODE_THIN:
      return 'Legacy: clean link, no attribution';
    default:
      return mode;
  }
};

/**
 * What each mode does to the researcher's data.
 *
 * Attribution cannot be fully hidden, because the mode changes the *shape of
 * what the researcher gets out* for any analysis outside the standard
 * swoosh -> inference_data pipeline. With thick, the stratum values ride inline
 * in every response's metadata and the export already has `gender`, `region`
 * columns. With encoded, the response carries a token and the stratum lives in
 * a separate table joined on `ref_token`.
 *
 * So the one thing to inform is not "encoded vs thick" but where the stratum
 * data ends up and what the key is. Give them the table and name the key: that
 * is the researcher-facing contract.
 */
export const refModeConsequence = (mode: string): string => {
  switch (mode) {
    case REF_MODE_ENCODED:
      return (
        'Respondents see a short, opaque link. Their stratum is not in the ' +
        'survey data — it comes from the ad-attributions export, joined on ' +
        'ref_token. Works the same on every channel.'
      );
    case REF_MODE_THICK:
      return (
        'Stratum values ride inline in every response, so your export already ' +
        'has gender, region and the rest as columns — nothing to join. The ' +
        'link is long and, on WhatsApp, visible and editable by the ' +
        'respondent, which is why this is Messenger-only.'
      );
    case REF_MODE_THIN:
      return (
        'This destination carries a clean link that attributes nobody. It ' +
        'predates the current options and is no longer offered — switch it to ' +
        'a clean link with attribution.'
      );
    default:
      return '';
  }
};

/**
 * The modes offered for one destination, given the study it sits in.
 *
 * `storedMode` is surfaced as an extra entry when it is something no longer
 * offered — today only a legacy "shortcode" conf. The census says that
 * population is zero, but showing a destination's real mode beats displaying
 * one it does not have, and it gives the researcher a way to see and change it.
 * Callers render that entry disabled: it is a current value, not a choice.
 */
export const refModeOptions = (
  destinationType: string,
  destinations: Destination[],
  storedMode?: string
): { name: string; label: string; disabled?: boolean }[] => {
  if (!carriesRefMode(destinationType)) return [];

  const options: { name: string; label: string; disabled?: boolean }[] = [
    { name: REF_MODE_ENCODED, label: refModeLabel(REF_MODE_ENCODED) },
  ];

  if (destinationType === MESSENGER && isPureMessengerStudy(destinations)) {
    options.push({ name: REF_MODE_THICK, label: refModeLabel(REF_MODE_THICK) });
  }

  if (storedMode && !options.some(o => o.name === storedMode)) {
    options.push({
      name: storedMode,
      label: refModeLabel(storedMode),
      disabled: true,
    });
  }

  return options;
};

/**
 * The mode to SHOW for a destination — never the mode to write.
 *
 * This is the load-bearing half of "the model defaults to legacy, the UI
 * defaults to encoded". An absent `ref_mode` is not missing data: it means the
 * conf was written before this feature existed, and adopt still resolves it
 * from the legacy `include_metadata_in_ref` flag, per channel. Messenger
 * defaults that flag True, so absent means thick; WhatsApp and multi default it
 * False, so absent means thin.
 *
 * Displaying the UI default instead would tell a researcher their legacy study
 * is encoded when it is not — and if that displayed value were ever written
 * back, opening a legacy study to fix a typo in its welcome message would flip
 * a running study's ads. Hence: display only. The default for a NEW conf lives
 * in initialRefMode, and reaches the form through the empty states in
 * Destination.tsx / Destinations.tsx.
 */
export const displayedRefMode = (
  storedMode: string | undefined,
  destinationType: string
): string => {
  if (storedMode) return storedMode;

  return destinationType === MESSENGER ? REF_MODE_THICK : REF_MODE_THIN;
};

/**
 * The mode a NEW destination is created with.
 *
 * Encoded everywhere, so there is one answer to "how do I get the stratum for
 * this respondent": join on ref_token, same for every channel. Because the UI
 * writes this explicitly into every new conf, an absent `ref_mode` in the
 * database comes to mean exactly one thing — created before this feature
 * existed — which makes "is this a legacy study?" a one-field check, and
 * distinguishes "chose thick deliberately" from "predates the choice".
 */
export const initialRefMode = (): RefMode => REF_MODE_ENCODED;

/**
 * Whether a saved destination is about to change the mode its ads are built
 * with, which is what the flip warning gates on.
 *
 * False for a destination that had no stored mode and has not been touched:
 * absent is a real state, and leaving it alone is not a change. It becomes true
 * as soon as an explicit mode differs from what was loaded — including
 * absent -> explicit, because writing "metadata" onto a legacy Messenger conf
 * changes nothing about the ads but writing "encoded" onto it changes all of
 * them, and the caller cannot tell those apart without comparing resolved
 * modes.
 */
export const refModeWouldChange = (
  loadedMode: string | undefined,
  currentMode: string | undefined,
  destinationType: string
): boolean =>
  displayedRefMode(loadedMode, destinationType) !==
  displayedRefMode(currentMode, destinationType);

/**
 * What a flip actually costs, which is not what people expect.
 *
 * Not data loss. swoosh's extraction is additive: a conf that finds nothing is
 * skipped rather than failed, and the two eras partition by presence of the
 * token — a thick-era respondent satisfies the inline conf and skips the
 * lookup, an encoded-era respondent does the reverse — so both eras attribute
 * as long as the old read conf is kept alongside the new one.
 *
 * The real cost is on the write side. The ref is part of the creative, and
 * reconciliation compares creatives, so changing the mode makes every existing
 * ad look drifted and rewrites all of them on the next run.
 */
export const REF_MODE_FLIP_WARNING =
  'Changing this rewrites every ad in this study on the next reconciliation ' +
  'run, because the link is part of the creative. That means real spend, ' +
  'possibly another Meta review, and the ad learning phase starting over. ' +
  'Live posts that people have already shared will start pointing at the new ' +
  'link too. Your existing respondents keep their attribution.';
