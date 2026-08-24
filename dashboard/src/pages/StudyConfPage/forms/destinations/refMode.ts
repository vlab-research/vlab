/**
 * Pure logic for how a destination's ads carry attribution.
 *
 * A recruitment ad carries a **ref** — the string that comes back to vlab, or
 * to the researcher's own survey, when someone clicks it. There is exactly one
 * question about it, and it is the same question on every channel:
 *
 *   thick      `creative.X.gender.women.form.Y` — the stratum rides inline, so
 *              it is already in the response data and there is nothing to join.
 *   encoded    an opaque token — the response carries the token and the stratum
 *              comes off the ad-attributions export, joined on it.
 *
 * That is the whole of this module. Which destination type it is, which other
 * destinations the study has, and whether anything reads the token back are all
 * somebody else's business: reading is configured in Data Extraction, and the
 * two sides are independent by design. A destination that emits a token nothing
 * reads is warned about once per reconciliation run, not prevented here.
 *
 * See documentation/ad-attributions.md.
 */
import { RefMode } from '../../../../types/conf';

export const REF_MODE_ENCODED = 'encoded';

/**
 * Thick's stored name is "metadata" — it says what the ref carries, which is
 * the whole stratum metadata. Named as a constant because the string is a
 * contract with adopt's RefMode literal, not a label; the label is in
 * refModeLabel.
 */
export const REF_MODE_THICK = 'metadata';

export const refModeLabel = (mode: string): string =>
  mode === REF_MODE_THICK
    ? 'Stratum values inline in the link'
    : 'Clean link — look the stratum up afterwards';

/**
 * What each mode does to the researcher's data.
 *
 * Attribution cannot be fully hidden, because the mode changes the *shape of
 * what the researcher gets out* for any analysis outside the standard
 * swoosh -> inference_data pipeline. With thick, the stratum values ride inline
 * in every response's metadata and the export already has `gender`, `region`
 * columns. With encoded, the response carries a token and the stratum lives in
 * a separate table joined on the token.
 *
 * So the one thing to inform is not "encoded vs thick" but where the stratum
 * data ends up and what the key is. Give them the table and name the key: that
 * is the researcher-facing contract.
 */
export const refModeConsequence = (mode: string): string =>
  mode === REF_MODE_THICK
    ? 'Stratum values ride inline in every response, so your export already ' +
      'has gender, region and the rest as columns — nothing to join. The link ' +
      'is long, and wherever the respondent can see it, they can edit it.'
    : 'Respondents see a short, opaque link. Their stratum is not in the ' +
      'survey data — it comes from the ad-attributions export, joined on the ' +
      'token. Set up the matching variable in Data Extraction.';

/** Both modes, everywhere. There is nothing about a channel that removes one. */
export const refModeOptions = (): { name: string; label: string }[] =>
  [REF_MODE_ENCODED, REF_MODE_THICK].map(name => ({
    name,
    label: refModeLabel(name),
  }));

/**
 * The mode to SHOW for a destination — never the mode to write.
 *
 * An absent `ref_mode` is not missing data: it means the conf was written
 * before this feature existed, and adopt resolves it to the inline ref.
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
 * Because the UI writes this explicitly into every new conf, an absent
 * `ref_mode` in the database comes to mean exactly one thing — created before
 * this feature existed — which makes "is this a legacy study?" a one-field
 * check, and distinguishes "chose thick deliberately" from "predates the
 * choice".
 */
export const initialRefMode = (): RefMode => REF_MODE_ENCODED;

/**
 * Whether a saved destination is about to change the mode its ads are built
 * with, which is what the flip warning gates on.
 *
 * Compared through displayedRefMode so that absent and an explicit "metadata"
 * count as the same thing: writing "metadata" onto a legacy conf changes no ad,
 * while writing "encoded" onto it changes all of them.
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
