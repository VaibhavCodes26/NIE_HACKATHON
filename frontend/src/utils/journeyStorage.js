/**
 * Journey storage keys used for temporary planning session state.
 * These are strictly separate from auth tokens ('np_auth_token')
 * and user preferences ('np_lang').
 */
export const JOURNEY_STORAGE_KEYS = [
  'np_journey_config',
  'np_selected_itinerary',
  'np_route_discovery_state',
  'np_journey_processed',
];

/**
 * Clears all temporary journey planning state from sessionStorage.
 * Leaves authentication and persistent user data completely untouched.
 */
export function clearJourneyPlanningSession() {
  try {
    for (const key of JOURNEY_STORAGE_KEYS) {
      sessionStorage.removeItem(key);
    }
  } catch (err) {
    console.error('Failed to clear journey temporary storage:', err);
  }
}
