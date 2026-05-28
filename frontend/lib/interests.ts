/** Interest tag labels — maps curated tag keys to display names.
 * Since curated tags are already human-readable (e.g., "Generative AI"),
 * this is mostly a pass-through, but provides a place for any overrides.
 */
export function interestLabel(tag: string): string {
  return tag;
}
