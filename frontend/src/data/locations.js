
// frontend/src/data/locations.js
// Curated suggestions for the Route Discovery page.
// These lists are NOT the full set of searchable locations.
// LocationField should also fetch matching locations dynamically from Geoapify.

export const START_LOCATIONS = [
  // Karnataka cities
  { id: 'blr', name: 'Bengaluru', type: 'city', hint: 'Karnataka capital', lat: 12.9716, lng: 77.5946 },
  { id: 'mys', name: 'Mysuru', type: 'city', hint: 'City of Palaces', lat: 12.2958, lng: 76.6394 },
  { id: 'mng', name: 'Mangaluru', type: 'city', hint: 'Coastal Karnataka', lat: 12.9141, lng: 74.856 },
  { id: 'hub', name: 'Hubballi', type: 'city', hint: 'North Karnataka hub', lat: 15.3647, lng: 75.124 },
  { id: 'blg', name: 'Belagavi', type: 'city', hint: 'Northern Karnataka', lat: 15.8497, lng: 74.4977 },
  { id: 'shv', name: 'Shivamogga', type: 'city', hint: 'Gateway to Malnad', lat: 13.9299, lng: 75.5681 },
  { id: 'bly', name: 'Ballari', type: 'city', hint: 'Near Hampi', lat: 15.1394, lng: 76.9214 },
  { id: 'vjp', name: 'Vijayapura', type: 'city', hint: 'Historic North Karnataka', lat: 16.8302, lng: 75.71 },
  { id: 'klb', name: 'Kalaburagi', type: 'city', hint: 'Kalyana Karnataka', lat: 17.3297, lng: 76.8343 },
  { id: 'udp', name: 'Udupi', type: 'city', hint: 'Temple town on the coast', lat: 13.3409, lng: 74.7421 },
  { id: 'dav', name: 'Davanagere', type: 'city', hint: 'Central Karnataka', lat: 14.4644, lng: 75.9218 },
  { id: 'tum', name: 'Tumakuru', type: 'city', hint: 'Karnataka city', lat: 13.3379, lng: 77.1173 },
  { id: 'has', name: 'Hassan', type: 'city', hint: 'Gateway to Belur and Halebidu', lat: 13.0033, lng: 76.1004 },
  { id: 'kar', name: 'Karwar', type: 'city', hint: 'Coastal Karnataka', lat: 14.8136, lng: 74.1297 },
  { id: 'mad', name: 'Madikeri', type: 'city', hint: 'Coorg hill town', lat: 12.4244, lng: 75.7382 },

  // Major Indian cities for convenient suggestions
  { id: 'mum', name: 'Mumbai', type: 'city', hint: 'Maharashtra', lat: 19.076, lng: 72.8777 },
  { id: 'pun', name: 'Pune', type: 'city', hint: 'Maharashtra', lat: 18.5204, lng: 73.8567 },
  { id: 'del', name: 'New Delhi', type: 'city', hint: 'National capital region', lat: 28.6139, lng: 77.209 },
  { id: 'hyd', name: 'Hyderabad', type: 'city', hint: 'Telangana', lat: 17.385, lng: 78.4867 },
  { id: 'che', name: 'Chennai', type: 'city', hint: 'Tamil Nadu', lat: 13.0827, lng: 80.2707 },
  { id: 'kochi', name: 'Kochi', type: 'city', hint: 'Kerala', lat: 9.9312, lng: 76.2673 },
  { id: 'goa', name: 'Panaji', type: 'city', hint: 'Goa', lat: 15.4909, lng: 73.8278 },
  { id: 'kol', name: 'Kolkata', type: 'city', hint: 'West Bengal', lat: 22.5726, lng: 88.3639 },
  { id: 'ahm', name: 'Ahmedabad', type: 'city', hint: 'Gujarat', lat: 23.0225, lng: 72.5714 },
  { id: 'jai', name: 'Jaipur', type: 'city', hint: 'Rajasthan', lat: 26.9124, lng: 75.7873 },
  { id: 'var', name: 'Varanasi', type: 'city', hint: 'Uttar Pradesh', lat: 25.3176, lng: 82.9739 },
  { id: 'bho', name: 'Bhopal', type: 'city', hint: 'Madhya Pradesh', lat: 23.2599, lng: 77.4126 },

  // Common Bengaluru transport hubs
  { id: 'blr-city-railway', name: 'KSR Bengaluru City Railway Station', type: 'station', hint: 'SBC railway station, Majestic', lat: 12.9767, lng: 77.5713 },
  { id: 'blr-cantonment', name: 'Bengaluru Cantonment Railway Station', type: 'station', hint: 'Bengaluru railway station', lat: 12.9937, lng: 77.5982 },
  { id: 'blr-yesvantpur', name: 'Yesvantpur Junction', type: 'station', hint: 'YPR railway station', lat: 13.0238, lng: 77.5502 },
  { id: 'blr-airport', name: 'Kempegowda International Airport', type: 'landmark', hint: 'Bengaluru airport, BLR', lat: 13.1986, lng: 77.7066 },
  { id: 'blr-mg-road', name: 'MG Road Metro Station', type: 'station', hint: 'Namma Metro, Bengaluru', lat: 12.9756, lng: 77.6066 },
];

export const DESTINATIONS = [
  // Karnataka heritage and city attractions
  { id: 'lalbagh', name: 'Lalbagh Botanical Garden', type: 'landmark', hint: 'Gardens and glasshouse, Bengaluru', lat: 12.9507, lng: 77.5848 },
  { id: 'bengaluru-palace', name: 'Bengaluru Palace', type: 'landmark', hint: 'Royal palace, Bengaluru', lat: 12.9987, lng: 77.592 },
  { id: 'vidhana-soudha', name: 'Vidhana Soudha', type: 'landmark', hint: 'Karnataka legislature, Bengaluru', lat: 12.9797, lng: 77.5907 },
  { id: 'cubbon-park', name: 'Cubbon Park', type: 'landmark', hint: 'Central Bengaluru green space', lat: 12.9763, lng: 77.5929 },
  { id: 'iskcon-bengaluru', name: 'ISKCON Temple Bengaluru', type: 'landmark', hint: 'Rajajinagar temple', lat: 13.0108, lng: 77.5511 },
  { id: 'mys-palace', name: 'Mysuru Palace', type: 'landmark', hint: 'Mysuru royal heritage', lat: 12.3052, lng: 76.6552 },
  { id: 'hampi', name: 'Hampi', type: 'landmark', hint: 'UNESCO World Heritage Site', lat: 15.335, lng: 76.46 },
  { id: 'badami', name: 'Badami Cave Temples', type: 'landmark', hint: 'Chalukyan cave temples', lat: 15.9149, lng: 75.6768 },
  { id: 'gol-gumbaz', name: 'Gol Gumbaz', type: 'landmark', hint: 'Historic monument, Vijayapura', lat: 16.8302, lng: 75.7367 },
  { id: 'coorg', name: 'Coorg', type: 'region', hint: 'Coffee hills and mist', lat: 12.4244, lng: 75.7382 },
  { id: 'gokarna', name: 'Gokarna', type: 'region', hint: 'Beaches and pilgrimage', lat: 14.5479, lng: 74.3188 },
  { id: 'chikkamagaluru', name: 'Chikkamagaluru', type: 'region', hint: 'Coffee country', lat: 13.3161, lng: 75.772 },
  { id: 'jog-falls', name: 'Jog Falls', type: 'landmark', hint: 'Sharavathi river waterfall', lat: 14.2294, lng: 74.8125 },
  { id: 'belur-temple', name: 'Chennakeshava Temple, Belur', type: 'landmark', hint: 'Historic Hoysala architecture', lat: 13.1631, lng: 75.865 },
  { id: 'halebidu', name: 'Hoysaleswara Temple, Halebidu', type: 'landmark', hint: 'Hoysala heritage', lat: 13.2128, lng: 75.9952 },
  { id: 'murudeshwar', name: 'Murudeshwar Temple', type: 'landmark', hint: 'Coastal temple and sea views', lat: 14.0946, lng: 74.4845 },
  { id: 'pattadakal', name: 'Pattadakal', type: 'landmark', hint: 'UNESCO World Heritage Site', lat: 15.948, lng: 75.816 },
  { id: 'bandipur', name: 'Bandipur National Park', type: 'landmark', hint: 'Wildlife and forest reserve', lat: 11.665, lng: 76.629 },

  // Popular destinations elsewhere in India
  { id: 'gateway-india', name: 'Gateway of India', type: 'landmark', hint: 'Mumbai, Maharashtra', lat: 18.922, lng: 72.8347 },
  { id: 'taj-mahal', name: 'Taj Mahal', type: 'landmark', hint: 'Agra, Uttar Pradesh', lat: 27.1751, lng: 78.0421 },
  { id: 'india-gate', name: 'India Gate', type: 'landmark', hint: 'New Delhi', lat: 28.6129, lng: 77.2295 },
  { id: 'golden-temple', name: 'Golden Temple', type: 'landmark', hint: 'Amritsar, Punjab', lat: 31.62, lng: 74.8765 },
  { id: 'charminar', name: 'Charminar', type: 'landmark', hint: 'Hyderabad, Telangana', lat: 17.3616, lng: 78.4747 },
  { id: 'marina-beach', name: 'Marina Beach', type: 'landmark', hint: 'Chennai, Tamil Nadu', lat: 13.0500, lng: 80.2824 },
  { id: 'howrah-bridge', name: 'Howrah Bridge', type: 'landmark', hint: 'Kolkata, West Bengal', lat: 22.5851, lng: 88.3468 },
  { id: 'amer-fort', name: 'Amer Fort', type: 'landmark', hint: 'Jaipur, Rajasthan', lat: 26.9855, lng: 75.8513 },
  { id: 'statue-unity', name: 'Statue of Unity', type: 'landmark', hint: 'Kevadia, Gujarat', lat: 21.838, lng: 73.7191 },

  // Karnataka cities are also valid destinations
  ...START_LOCATIONS
    .filter((location) =>
      location.type === 'city' &&
      !['mum', 'pun', 'del', 'hyd', 'che', 'kochi', 'goa', 'kol', 'ahm', 'jai', 'var', 'bho'].includes(location.id)
    )
    .map((location) => ({
      ...location,
      hint: location.hint || 'Karnataka city',
    })),
];

export const HERO_QUOTES = [
  'Where every road leads to a story.',
  'A land of ancient empires, living traditions and unforgettable flavours.',
  'From royal palaces to coastal sunsets, Karnataka awaits.',
];

export const HERO_IMAGE = '/images/karnataka-hero.jpg';

export const SHOWCASE = [
  { name: 'Hampi', tag: 'Ruins of an empire' },
  { name: 'Mysuru', tag: 'Royal heritage' },
  { name: 'Gokarna', tag: 'Golden shores' },
  { name: 'Coorg', tag: 'Misty hills' },
];
