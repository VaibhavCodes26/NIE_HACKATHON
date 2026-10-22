import { commonsImg, commonsPage } from './destinations';

// `file: null` => no verified photo has been sourced yet; the UI shows an honest
// illustrated fallback tile. Add a Commons filename here and it will appear automatically.
export const CATEGORIES = [
  {
    id: 'temples', icon: 'Landmark', tone: ['#7a1218', '#c8472e'], file: 'Belur Chennakeshava Temple.jpg',
    intro: "Karnataka's temple traditions span the Chalukyas, Hoysalas and Vijayanagara rulers.",
    places: [
      ['Belur & Halebidu', 'Hoysala temples known for intricate stone carving.'],
      ['Pattadakal', 'A UNESCO World Heritage Site with Chalukya temples.'],
      ['Aihole', 'An early cradle of temple experiments in the Chalukya period.'],
      ['Somanathapura', 'The Chennakesava Temple, another Hoysala masterpiece.'],
    ],
  },
  {
    id: 'hills', icon: 'Mountain', tone: ['#1f5a3d', '#6d9a5b'], file: 'Jog Falls - September 2024 15.jpg',
    intro: "The Western Ghats, a UNESCO-listed biodiversity region, run along Karnataka's west.",
    places: [
      ['Kodagu (Coorg)', 'Coffee estates, rain-fed hills and misty viewpoints.'],
      ['Chikkamagaluru', "Home to Mullayanagiri, Karnataka's highest peak."],
      ['Kudremukh', 'Grassland ridges and shola forests for trekkers.'],
      ['Agumbe', 'A rainforest village known for sunsets and monsoon rain.'],
    ],
  },
  {
    id: 'food', icon: 'UtensilsCrossed', tone: ['#b8741a', '#f4b82b'], file:'Dosa (36400591833).jpg',
    intro: "Karnataka's food changes every few hundred kilometres.", places: [],
  },
  {
    id: 'festivals', icon: 'Drama', tone: ['#8c2b4a', '#d9822b'], file: 'Lord Shiva Statue, Murdeshwar, Uttara Kannada, Karnataka, India (2018).jpg',
    intro: "Karnataka's calendar carries royal pageantry, folk theatre and village sport.",
    places: [
      ['Mysuru Dasara', 'A ten-day festival centred on the Mysore Palace.'],
      ['Yakshagana', 'A night-long dance-drama tradition of coastal Karnataka.'],
      ['Kambala', 'Traditional buffalo racing in the paddy fields of the coast.'],
      ['Hampi Utsav', 'A cultural festival held among the Vijayanagara ruins.'],
    ],
  },
  {
    id: 'coastal', icon: 'Waves', tone: ['#12607a', '#4fa3a5'], file: 'PXL 20260103 054657562.MP Paradise beach gokarna Paradise Beach Trail, Gokarna, Karnataka 581326 08.jpg',
    intro: "Karnataka's coastline stretches along the Arabian Sea with temples, beaches and distinctive cuisine.",
    places: [
      ['Gokarna', 'Temple town with quiet beaches such as Om Beach.'],
      ['Udupi', 'Famed for the Krishna Temple and its vegetarian cuisine.'],
      ['Murudeshwar', 'A seaside temple beneath a giant Shiva statue.'],
      ['Mangaluru', 'A port city with a distinct coastal food culture.'],
    ],
  },
  {
    id: 'historical', icon: 'Castle', tone: ['#5a3a22', '#b8864a'], file: 'Hampi, Vittala Temple, chariot (9881832023).jpg',
    intro: 'Forts, capitals and monuments that tell the story of the region across centuries.',
    places: [
      ['Hampi', 'The ruined capital of the Vijayanagara Empire.'],
      ['Vijayapura', 'Home to the Gol Gumbaz and Adil Shahi monuments.'],
      ['Chitradurga', 'A fort built among great granite boulders.'],
      ['Srirangapatna', 'An island town tied to the history of Mysore.'],
    ],
  },
].map((c) => ({
  ...c,
  img: c.file ? commonsImg(c.file, 700) : null,
  credit: c.file ? commonsPage(c.file) : null,
}));

export const DISHES = [
  { id: 'dosa', name: 'Mysore masala dosa', note: 'Crisp dosa with a red chutney layer and spiced potato filling.' },
  { id: 'bisi', name: 'Bisi bele bath', note: 'A hot, spiced rice-and-lentil dish, often served with boondi.' },
  { id: 'mudde', name: 'Ragi mudde', note: 'Finger-millet balls eaten with saaru or curry, common in southern Karnataka.' },
  { id: 'rotti', name: 'Jolada rotti', note: 'Sorghum flatbread central to North Karnataka meals.' },
  { id: 'peda', name: 'Dharwad peda', note: 'A caramelised milk sweet associated with Dharwad.' },
  { id: 'mangalore', name: 'Mangalorean cuisine', note: 'Coastal cooking with coconut, seafood and dishes such as neer dosa.' },
];
