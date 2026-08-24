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
 * Two modes exist here:
 *
 *   encoded    `r.<token>` — clean AND attributes, via the ad_attributions
 *              join on ref_token. The default, on every channel.
 *   thick      `creative.X.gender.women.form.Y` — everything inline, no DB.
 *              Correct and free on Messenger (the ref is invisible there), so
 *              it stays available as the legacy-but-useful path.
 *
 * Two, and only two, in adopt as well: RefMode is `"metadata" | "encoded"`.
 * A ref either carries the stratum or carries a token that resolves to it;
 * "carry neither" attributes nobody, which is not something anyone chooses. A
 * study with no stratification simply has a short ref, because
 * creative_metadata has nothing to put in it — thick with nothing to say.
 *
 * The destination-type census is why an absent `ref_mode` needs no per-channel
 * reasoning: 892 messenger, 11 web, 3 website, 0 whatsapp, 0 multi, so every
 * legacy conf is a Messenger one and absent means thick. See displayedRefMode.
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

export const MESSENGER = 'messenger';
export const WHATSAPP = 'whatsapp';
export const MULTI = 'multi';

/**
 * The destination types that carry a ref mode at all.
 *
 * Web and app destinations are absent, and the reason is the read side rather
 * than the write side. They do get a ref: `create_creative` builds the same
 * full `make_ref` string for them and interpolates it into url_template /
 * deeplink_template, so their ads already carry the stratum inline. What they
 * have no way to do is the other mode.
 *
 * An encoded ref is only worth emitting if something can resolve the token, and
 * for these two nothing can. Their respondent lands on the researcher's own
 * page, so their data comes back through a Qualtrics or Typeform source rather
 * than through fly — and the lookup resolves out of fly-stamped event metadata
 * only. swoosh's `isAdTableLookup` requires `location: "metadata"` and errors
 * loudly on a lookup conf declared anywhere else, while the Qualtrics/Typeform
 * form offers no mapping dropdown at all. A web destination set to encoded
 * would mint a token that lands in a survey field no conf can read: ads that
 * attribute nobody, which is the exact failure ref_mode_incoherence exists to
 * refuse.
 *
 * So this is a gap, not a category difference — offering both modes here is a
 * real feature, and it is the read side that has to move first. It needs
 * `ad_table_lookup` to resolve from a survey field on a non-fly source, which
 * is the `variable` + `ad_table_lookup` hole documentation/ad-attributions.md
 * already calls out. Until then, listing web and app here would offer a choice
 * whose second option cannot work.
 */
export const REF_MODE_DESTINATION_TYPES = [MESSENGER, WHATSAPP, MULTI];

export const carriesRefMode = (destinationType: string): boolean =>
  REF_MODE_DESTINATION_TYPES.includes(destinationType);

/**
 * Whether every fly destination in the study is Messenger.
 *
 * Thick is offered on pure-Messenger studies only. Its one cost — a visible,
 * editable ref sitting in the respondent's compose box — lands entirely on the
 * WhatsApp arm, so offering it to a study that has any WhatsApp or multi
 * destination would reintroduce the per-channel heterogeneity the encoded
 * default exists to remove: that study would attribute two different ways, and
 * the researcher would join their data two different ways depending on which
 * arm a respondent arrived through. That confusion surfaces at analysis time,
 * months later, to someone who was not in the room.
 */
export const isPureMessengerStudy = (destinations: Destination[]): boolean => {
  const flyDestinations = destinations
    .map(d => (d as { type?: string }).type || '')
    .filter(carriesRefMode);

  return flyDestinations.length > 0 && flyDestinations.every(t => t === MESSENGER);
};

export const refModeLabel = (mode: string): string =>
  mode === REF_MODE_THICK
    ? 'Stratum values inline in the link (Messenger only)'
    : 'Clean link — look the stratum up afterwards';

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
export const refModeConsequence = (mode: string): string =>
  mode === REF_MODE_THICK
    ? 'Stratum values ride inline in every response, so your export already ' +
      'has gender, region and the rest as columns — nothing to join. The link ' +
      'is long and, on WhatsApp, visible and editable by the respondent, ' +
      'which is why this is Messenger-only.'
    : 'Respondents see a short, opaque link. Their stratum is not in the ' +
      'survey data — it comes from the ad-attributions export, joined on ' +
      'ref_token. Works the same on every channel.';

/**
 * The modes offered for one destination, given the study it sits in.
 *
 * Encoded always; thick as well on a pure-Messenger study.
 *
 * There is deliberately no `destinationType === MESSENGER` check alongside
 * `isPureMessengerStudy`: it would be redundant. This destination is one of
 * `destinations`, so if the study is pure Messenger then this destination is a
 * Messenger one, and if it is not then the study is not pure.
 */
export const refModeOptions = (
  destinations: Destination[]
): { name: string; label: string }[] => {
  const modes = isPureMessengerStudy(destinations)
    ? [REF_MODE_ENCODED, REF_MODE_THICK]
    : [REF_MODE_ENCODED];

  return modes.map(name => ({ name, label: refModeLabel(name) }));
};

/**
 * The mode to SHOW for a destination — never the mode to write.
 *
 * This is the load-bearing half of "the model defaults to legacy, the UI
 * defaults to encoded". An absent `ref_mode` is not missing data: it means the
 * conf was written before this feature existed, and every such conf is a thick
 * Messenger one.
 *
 * Displaying the UI default instead would tell a researcher their legacy study
 * is encoded when it is not — and if that displayed value were ever written
 * back, opening a legacy study to fix a typo in its welcome message would flip
 * a running study's ads. Hence: display only. The default for a NEW conf lives
 * in initialRefMode, and reaches the form through the empty states in
 * Destination.tsx / Destinations.tsx.
 */
export const displayedRefMode = (storedMode: string | undefined): string =>
  storedMode || REF_MODE_THICK;

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
 * Compared through displayedRefMode so that absent and an explicit "metadata"
 * count as the same thing: writing "metadata" onto a legacy Messenger conf
 * changes no ad, while writing "encoded" onto it changes all of them.
 */
export const refModeWouldChange = (
  loadedMode: string | undefined,
  currentMode: string | undefined
): boolean => displayedRefMode(loadedMode) !== displayedRefMode(currentMode);

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
