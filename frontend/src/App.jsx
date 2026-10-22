
import { useCallback, useEffect, useState } from 'react';

import Intro from './components/Intro';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import Discovery from './components/Discovery';
import Panels from './components/Panels';
import { FoodSection, AboutSection, Footer } from './components/Sections';

import PlanJourney from './components/Planjourney';
import RouteDiscoveryPage from './RouteDiscovery';
import FoodSpots from './FoodSpots.jsx';
import Stays from './Stays';
import './styles.css';
import './route-discovery.css';
import './FoodSpots.css';
import ItineraryPage from "./ItineraryPage.jsx";


const reduced = () =>
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

const isLandingPageReload = () => {
  const navigationEntry = performance.getEntriesByType('navigation')[0];

  return (
    window.location.pathname === '/' &&
    navigationEntry?.type === 'reload'
  );
};


export default function App() {
  const [journeyConfig, setJourneyConfig] = useState(null);


const [intro, setIntro] = useState(
  () => isLandingPageReload() && !reduced()
);

  const [panel, setPanel] = useState(null);
  const [active, setActive] = useState('home');

  const [currentPage, setCurrentPage] = useState(
    () => window.location.pathname
  );
  const [selectedAttractionIds, setSelectedAttractionIds] = useState(() => {
  try {
    const saved = sessionStorage.getItem('np_selected_itinerary');
    return saved
      ? JSON.parse(saved).selected_attraction_ids ?? []
      : [];
  } catch (error) {
    console.error('Unable to read saved itinerary:', error);
    return [];
  }
});

  // Support browser Back and Forward navigation.
  useEffect(() => {
    const handlePopState = () => {
      setCurrentPage(window.location.pathname);
      setPanel(null);
    };

    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  // Navigate between pages without reloading the application.
  const navigate = useCallback((path) => {
    if (window.location.pathname !== path) {
      window.history.pushState({}, '', path);
    }

    setCurrentPage(path);
    setPanel(null);
    window.scrollTo(0, 0);
  }, []);
  const handleOpenItinerary = () => {
  navigate("/itinerary");
};

  
const finishIntro = useCallback(() => {
  setIntro(false);
}, []);


  const scrollTo = (id) => {
    document.getElementById(id)?.scrollIntoView({
      behavior: reduced() ? 'auto' : 'smooth',
      block: 'start',
    });
  };

  const onNav = (id) => {
    setActive(id);

    if (id === 'plan') {
      navigate('/plan-journey');
      return;
    }

    if (id === 'help') {
      setPanel({ type: id });
      return;
    }

    if (currentPage !== '/') {
      navigate('/');

      if (id !== 'home') {
        requestAnimationFrame(() => scrollTo(id));
      }

      return;
    }

    scrollTo(id);
  };

  // Open the dedicated Food Spots page.
  const openFood = () => {
    setActive('food');
    navigate('/food-spots');
  };

  const onCategory = (id) =>
    id === 'food'
      ? openFood()
      : setPanel({ type: 'category', id });

  const close = useCallback(() => setPanel(null), []);

  const onDestination = (id) =>
    setPanel({ type: 'destination', id });

  // Page 1: Journey preferences.
  if (currentPage === '/plan-journey') {
    return (
      <PlanJourney
        onBack={() => navigate('/')}
        onDiveIntoJourney={(preferences) => {
          setJourneyConfig(preferences);
          navigate('/route-discovery');
        }}
      />
    );
  }

  // Page 2: Route discovery, transport and tourism itinerary.
  if (currentPage === '/route-discovery') {
    return (
      <RouteDiscoveryPage
        initialDestinations={journeyConfig?.destinations ?? []}
        initialStartDate={journeyConfig?.startDate}
        initialEndDate={journeyConfig?.endDate}
        onContinue={() => navigate('/plan-journey')}
        onOpenStays={() => navigate('/stays')}
        onOpenItinerary={() => navigate('/itinerary')}
      />
    );
  }
  // stay page 
  if (currentPage === '/stays') {
  return (
    <Stays
      journeyConfig={journeyConfig}
      onBack={() => navigate('/route-discovery')}
    />
  );
}

  // Page 3: Dedicated Food Spots page.
  if (currentPage === '/food-spots') {
    return (
    <FoodSpots
     onBack={() => navigate('/route-discovery')} />
  );
  }
  //page 4 : itinerary page 
  // Page 4: Itinerary page
if (currentPage === '/itinerary') {
  return (
    <ItineraryPage
      journeyConfig={journeyConfig}
      selectedAttractionIds={selectedAttractionIds}
      onBack={() => navigate('/route-discovery')}
    />
  );
}

  // Default page: Existing landing page.
  return (
    <>
      <a className="skip-link" href="#home">
        Skip to content
      </a>

      <Navbar active={active} onNav={onNav} />

      <main>
        <Hero
          onPlan={() => onNav('plan')}
          onFood={openFood}
          onCategory={onCategory}
          onDestination={onDestination}
        />

        <Discovery onCategory={onCategory} />

        <FoodSection />

        <AboutSection />
      </main>

      <Footer />

      <Panels panel={panel} onClose={close} />

      {intro && <Intro onDone={finishIntro} />}
    </>
  );
}