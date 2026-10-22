// Photos are hot-linked from Wikimedia Commons via Special:FilePath (resized server-side).
// Filenames were taken from Commons category listings. Each Commons file has its own
// author + licence on its file page, which is linked from the photo credit in the UI.
const norm = (f) => f.replace(/ /g, '_');
export const commonsImg = (file, width = 1400) =>
  `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(norm(file))}?width=${width}`;
export const commonsPage = (file) =>
  `https://commons.wikimedia.org/wiki/File:${encodeURIComponent(norm(file))}`;

export const DESTINATIONS = [
  {
    id: 'mysore',
    name: 'Mysore Palace',
    kn: 'ಮೈಸೂರು ಅರಮನೆ',
    file: 'Mysore Palace, Mysuru.jpg',
    overlay: 'Mysore Palace',
    heading: 'The Royal Heritage of Mysore',
    description:
      "Mysore Palace is a landmark of the city's royal history, associated with the Wadiyar dynasty. Its Indo-Saracenic architecture, ornate interiors and ceremonial traditions make it one of Karnataka's best-known heritage sites.",
    location: 'Mysuru, Mysuru district',
    alt: 'Front view of Mysore Palace in Mysuru, Karnataka',
    details: [
      'The present palace was built between 1897 and 1912, replacing an earlier wooden palace.',
      'Its style blends Hindu, Islamic, Rajput and Gothic elements, known as Indo-Saracenic.',
      'The palace is the focal point of Mysuru Dasara, the ten-day festival held each autumn.',
      'Roughly 150 km from Bengaluru; Mysuru is easily reached by road and rail.',
    ],
    more: 'https://en.wikipedia.org/wiki/Mysore_Palace',
  },
  {
    id: 'hampi',
    name: 'Hampi',
    kn: 'ಹಂಪಿ',
    file: 'Hampi, Vittala Temple, chariot (9881832023).jpg',
    overlay: 'Hampi',
    heading: 'Vijayanagara: A Capital of Stone',
    description:
      'Hampi lies within the ruins of Vijayanagara, capital of the empire of the same name in the 14th–16th centuries. Boulder-strewn hills, the Tungabhadra river, grand temples and the iconic stone chariot of the Vittala complex make it a UNESCO World Heritage Site.',
    location: 'Hampi, Vijayanagara district',
    alt: 'The stone chariot at the Vittala Temple complex in Hampi',
    details: [
      'The stone chariot is a shrine to Garuda, set in front of the Vittala Temple.',
      'The Virupaksha Temple is still an active place of worship at the heart of Hampi.',
      'Hampi was inscribed as a UNESCO World Heritage Site in 1986.',
      'Hosapete is the nearest major town and railhead.',
    ],
    more: 'https://en.wikipedia.org/wiki/Hampi',
  },
  {
    id: 'belur',
    name: 'Belur',
    kn: 'ಬೇಲೂರು',
    file: 'Belur Chennakeshava Temple.jpg',
    overlay: 'Belur',
    heading: 'Hoysala Artistry in Stone',
    description:
      'The Chennakeshava Temple at Belur, commissioned by King Vishnuvardhana in 1117 CE, is celebrated for Hoysala craftsmanship: a star-shaped plan, richly sculpted walls and delicate bracket figures carved with extraordinary detail.',
    location: 'Belur, Hassan district',
    alt: 'The Chennakeshava Temple at Belur, a Hoysala-era temple in Karnataka',
    details: [
      'The temple stands on the banks of the Yagachi river and is dedicated to Vishnu.',
      'It was originally called the Vijayanarayana Temple.',
      'Belur was an early Hoysala capital; Halebidu and Somanathapura hold sister temples.',
      'The Hoysala temples of Belur, Halebidu and Somanathapura are on the UNESCO World Heritage List.',
    ],
    more: 'https://en.wikipedia.org/wiki/Chennakeshava_Temple,_Belur',
  },
  {
    id: 'gol Gombuz',
    name: 'Gol Gombuz',
    kn: 'ಗೋಲ ಗುಮ್ಮಟ',
    file: 'Gol Gumbaj2.JPG',
    overlay: 'Gol Gombuz',
    heading: 'Gol Gumbaz',
    description:
      'Gol Gumbaz is the grand mausoleum of King Mohammed Adil Shah, the seventh ruler of the Adil Shahi dynasty. Built in the 17th century, this iconic monument is a masterpiece of Indo-Islamic architecture and features the second-largest dome in the world, entirely unsupported by pillars.',
    location: 'Vijayapura (Bijapur), Vijayapura district',
    alt: 'The massive grey basalt dome of Gol Gumbaz with its four distinct octagonal minarets',
    details: [
      'The mausoleum houses the cenotaphs of Mohammed Adil Shah, his wives, his mistress, and his grandson.',
      'It is globally famous for its "Whispering Gallery", where even a soft whisper echoes up to eleven times across the dome.',
      'Architecturally unique, the colossal dome rests on a system of intersecting arches without any central column support.',
      'The complex includes a mosque, a well-maintained museum, and a gateway known as the Naqqar Khana (drum house).',
    ],

    more: 'https://en.wikipedia.org/wiki/Gol_Gumbaz',
  },
  {
    id: 'shravanabelagola',
    name: 'Shravanabelagola',
    kn: 'ಶ್ರವಣಬೆಳಗೊಳ',
    file: 'Shravanabelagola Bahubali wideframe.jpg',
    overlay: 'Shravanabelagola',
    heading: 'Gomateshwara and Jain Heritage',
    description:
      'Shravanabelagola is one of the most important Jain pilgrimage centres in India. On Vindhyagiri hill stands the monolithic statue of Gomateshwara (Bahubali), about 57 feet tall and commissioned in the 10th century by Chavundaraya, a minister of the Ganga dynasty.',
    location: 'Shravanabelagola, Hassan district',
    alt: 'The monolithic Gomateshwara statue of Bahubali on Vindhyagiri hill',
    details: [
      'The Mahamastakabhisheka, a ritual anointing of the statue, takes place once every 12 years; the most recent was in 2018.',
      'Chandragiri, the neighbouring hill, holds several older Jain monuments.',
      'Inscriptions around the site include some of the earliest known Kannada writing.',
      'The statue is reached by climbing steps cut into the granite of Vindhyagiri.',
    ],
    more: 'https://en.wikipedia.org/wiki/Gommateshwara_statue',
  },
  {
  id: 'yana-caves',
  name: 'Yana Caves',
  kn: 'ಯಾಣ ಗುಹೆಗಳು',
  file: 'Yana Rocks.jpg',
  overlay: 'Yana Caves',
  heading: 'Yana Caves',
  description:
    'Yana Caves are famous for their two massive monolithic rock outcrops—the Bhairaveshwara Shikhara and the Mohini Shikhara—composed of solid black crystalline limestone. Located deep within the evergreen forests of the Western Ghats, this unique geological wonder features a sacred cave temple dedicated to Lord Shiva.',
  location: 'Uttara Kannada district, Karnataka',
  alt: 'Massive black limestone rock monoliths of Yana rising amidst dense green Western Ghats forests',
  details: [
    'The site features two towering rock formations: the 120-meter-high Bhairaveshwara Shikhara and the 90-meter-high Mohini Shikhara.',
    'A cave temple sits at the base of the Bhairaveshwara Shikhara, housing a self-manifested Shiva linga where water constantly drips from the roof.',
    'According to Hindu mythology, the site is tied to the legend of the demon king Bhasmasura and Lord Vishnu in his Mohini avatar.',
    'Recognized as a protected natural geological wonder, it is a popular destination for trekkers and nature lovers alike.',
  ],
  more: 'https://en.wikipedia.org/wiki/Yana,_India',
},
];
