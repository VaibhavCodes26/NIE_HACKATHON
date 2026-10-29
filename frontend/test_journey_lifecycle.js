/**
 * Test suite for Journey Lifecycle and Stale State Reset
 */
import assert from 'node:assert';
import { clearJourneyPlanningSession, JOURNEY_STORAGE_KEYS } from './src/utils/journeyStorage.js';

console.log('Testing Journey Lifecycle & Session Storage Management...');

// Mock sessionStorage
const storage = new Map();
globalThis.sessionStorage = {
  getItem: (key) => storage.get(key) ?? null,
  setItem: (key, val) => storage.set(key, String(val)),
  removeItem: (key) => storage.delete(key),
  clear: () => storage.clear(),
  get length() { return storage.size; }
};

// 1. Setup initial state with an active journey AND an authenticated user session
const AUTH_TOKEN = 'mock-jwt-token-xyz-123';
const USER_LANG = 'kn';

sessionStorage.setItem('np_auth_token', AUTH_TOKEN);
sessionStorage.setItem('np_lang', USER_LANG);

// Journey 1 data
const journey1Config = {
  destinations: ['mysuru', 'coorg'],
  startDate: '2026-11-01',
  endDate: '2026-11-05',
  travellerCount: 2,
  travelStyle: 'comfortable',
  totalBudget: 25000,
  interests: ['Nature & hills', 'Local food']
};

const journey1Itinerary = {
  ...journey1Config,
  start_date: journey1Config.startDate,
  end_date: journey1Config.endDate,
  traveller_count: journey1Config.travellerCount,
  travel_style: journey1Config.travelStyle,
  total_budget: journey1Config.totalBudget,
  selected_attraction_ids: [101, 102, 103],
  selected_places: [{ id: 101, name: 'Mysore Palace' }],
  route_mode: 'DRIVE'
};

const journey1RouteState = {
  from: 'Bengaluru',
  to: 'Mysuru',
  selected: 'taxi',
  destinations: ['mysuru', 'coorg'],
  selectedAttractionIds: [101, 102, 103]
};

sessionStorage.setItem('np_journey_config', JSON.stringify(journey1Config));
sessionStorage.setItem('np_selected_itinerary', JSON.stringify(journey1Itinerary));
sessionStorage.setItem('np_route_discovery_state', JSON.stringify(journey1RouteState));
sessionStorage.setItem('np_journey_processed', 'true');

// Verify all are present
assert.strictEqual(sessionStorage.getItem('np_auth_token'), AUTH_TOKEN);
assert.strictEqual(sessionStorage.getItem('np_journey_config') !== null, true);
assert.strictEqual(sessionStorage.getItem('np_selected_itinerary') !== null, true);
assert.strictEqual(sessionStorage.getItem('np_route_discovery_state') !== null, true);
assert.strictEqual(sessionStorage.getItem('np_journey_processed'), 'true');
console.log('✓ Step 1: Active Journey 1 state and Auth token successfully seeded.');

// 2. Call clearJourneyPlanningSession()
clearJourneyPlanningSession();

// Verify all temporary journey keys were removed
for (const key of JOURNEY_STORAGE_KEYS) {
  assert.strictEqual(sessionStorage.getItem(key), null, `Key ${key} should have been removed!`);
}
console.log('✓ Step 2: All temporary journey keys removed by clearJourneyPlanningSession().');

// 3. Verify Authentication and Language preferences are PRESERVED
assert.strictEqual(sessionStorage.getItem('np_auth_token'), AUTH_TOKEN, 'Auth token must NOT be cleared!');
assert.strictEqual(sessionStorage.getItem('np_lang'), USER_LANG, 'Language settings must NOT be cleared!');
console.log('✓ Step 3: Auth session and user settings safely preserved.');

// 4. Simulate PlanJourney reading state after reset
function simulatePlanJourneyInit() {
  const raw = sessionStorage.getItem('np_journey_config');
  if (raw) return JSON.parse(raw);
  const rawItin = sessionStorage.getItem('np_selected_itinerary');
  if (rawItin) {
    const parsed = JSON.parse(rawItin);
    return {
      destinations: parsed.destinations ?? [],
      startDate: parsed.start_date,
      endDate: parsed.end_date,
      travellerCount: parsed.traveller_count,
      travelStyle: parsed.travel_style,
      totalBudget: parsed.total_budget,
      interests: parsed.interests,
    };
  }
  return null;
}

const restoredConfigAfterFinish = simulatePlanJourneyInit();
assert.strictEqual(restoredConfigAfterFinish, null, 'PlanJourney must find no saved config after finish.');
const selectedDestinations = restoredConfigAfterFinish?.destinations ?? [];
assert.deepStrictEqual(selectedDestinations, [], 'Selected destinations must be empty array!');
console.log('✓ Step 4: PlanJourney starts completely blank with empty destinations.');

// 5. Simulate Journey 2: select completely different cities (e.g. Hampi, Badami)
const journey2Config = {
  destinations: ['hampi', 'badami'],
  startDate: '2026-12-10',
  endDate: '2026-12-14',
  travellerCount: 4,
  travelStyle: 'premium',
  totalBudget: 40000,
  interests: ['Heritage & culture']
};

sessionStorage.setItem('np_journey_config', JSON.stringify(journey2Config));
sessionStorage.setItem('np_selected_itinerary', JSON.stringify({
  ...journey2Config,
  start_date: journey2Config.startDate,
  end_date: journey2Config.endDate,
  traveller_count: journey2Config.travellerCount,
  travel_style: journey2Config.travelStyle,
  total_budget: journey2Config.totalBudget,
  selected_attraction_ids: [201, 202],
  selected_places: [{ id: 201, name: 'Virupaksha Temple' }]
}));

const restoredJourney2 = simulatePlanJourneyInit();
assert.deepStrictEqual(restoredJourney2.destinations, ['hampi', 'badami']);
assert.strictEqual(restoredJourney2.destinations.includes('mysuru'), false, 'Old city Mysuru must not leak!');
assert.strictEqual(restoredJourney2.destinations.includes('coorg'), false, 'Old city Coorg must not leak!');
console.log('✓ Step 5: Journey 2 contains ONLY newly selected destinations (no stale leak).');

// 6. Test page reload simulation (sessionStorage remains empty after finish)
clearJourneyPlanningSession();
const afterReload = simulatePlanJourneyInit();
assert.strictEqual(afterReload, null, 'After reload when finished, session storage still has no stale state.');
console.log('✓ Step 6: Page refresh / reload test passed (no resurrection of stale state).');

console.log('\nAll Journey Lifecycle & Stale State tests passed successfully!');
