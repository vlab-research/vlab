/**
 * Pure logic for the ref-mode control.
 * No React dependencies; testable in isolation.
 *
 * A recruitment ad carries a **ref**: the string that comes back when someone
 * clicks it. `ref_mode` says what that string carries — the stratum inline, or
 * an opaque token that the ad-attributions export resolves back to it.
 *
 * It is independent of the extraction conf's `mapping`, the read side. Neither
 * validates, gates or reads the other: they are separate confs, POSTed to
 * separate endpoints, each saving on its own terms in any order.
 *
 * The words `ref_mode` and `encoded` never reach the screen. What a researcher
 * needs to decide is where their stratum data ends up and what the key is.
 */
import { RefMode } from '../../../../types/conf';

// Annotated rather than inferred, so the value keeps its literal type where a
// destination conf is built and the union still narrows.
export const METADATA_MODE: RefMode = 'metadata';
export const ENCODED_MODE: RefMode = 'encoded';

export type { RefMode };

/**
 * Both modes, always. There is nothing to decide it from: what a ref carries is
 * a property of the ref, not of the channel carrying it, so every destination
 * type offers the same two.
 */
export const refModeOptions = () => [
  {
    name: METADATA_MODE,
    label: 'In the data itself — gender and region arrive as columns',
  },
  {
    name: ENCODED_MODE,
    label: 'Looked up afterwards, from the ad-attributions export',
  },
];

/**
 * What a stored conf actually does, and never what to write back.
 *
 * An absent `ref_mode` is a real state: the conf predates the field. It resolves
 * to the behaviour it already has, which is what makes the migration free — so
 * this reports, and nothing writes its result onto a conf that arrived without
 * one. The default belongs to the empty-state constructors, which build new
 * confs, and the forms spread `...data`, so a field absent from a conf stays
 * absent through an unrelated edit.
 */
export const displayedRefMode = (stored: string | undefined): RefMode =>
  stored === ENCODED_MODE ? ENCODED_MODE : METADATA_MODE;

/**
 * Whether saving would change what a destination's ads emit.
 *
 * Compared through `displayedRefMode`, so an absent mode and an explicit
 * "metadata" count as the same thing — they describe the same ads.
 */
export const refModeChanges = (
  saved: string | undefined,
  next: string | undefined
): boolean => displayedRefMode(saved) !== displayedRefMode(next);

/**
 * What changing a saved destination's mode costs.
 *
 * The ref is part of the creative and reconciliation compares creatives, so
 * changing it rewrites every ad in the study on the next run.
 */
export const REF_MODE_CHANGE_WARNING =
  'Changing this rewrites every ad in this study on the next run: real spend, ' +
  'possibly another Meta review, and the learning phase starting over. Live ' +
  'posts people have already shared will start pointing at the new link. ' +
  'Respondents who already arrived keep the attribution they came with.';
