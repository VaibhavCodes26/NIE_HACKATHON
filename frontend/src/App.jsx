
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
import SahayakPage from "./SahayakPage.jsx";
import DrishtiPage from "./DrishtiPage.jsx";
import SahayakFab from "./components/SahayakFab";
import LoginPage from './LoginPage.jsx';
import SignupPage from './SignupPage.jsx';
import YourItinerariesPage from './YourItinerariesPage.jsx';
import LoginRequiredModal from './components/LoginRequiredModal.jsx';
import { useAuth } from './AuthContext.jsx';
import { Loader2 } from 'lucide-react';
import './auth.css';
import { clearJourneyPlanningSession } from './utils/journeyStorage';

const reduced = () =>
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;


const isLandingPageReload = () => {
  const navigationEntry = performance.getEntriesByType('navigation')[0];

  return (
    window.location.pathname === '/' &&
    (
      navigationEntry?.type === 'navigate' ||
      navigationEntry?.type === 'reload'
    )
  );
};

/** Protected pages — require authentication */
const PROTECTED_PATHS = new Set([
  '/plan-journey',
  '/route-discovery',
  '/itinerary',
  '/food-spots',
  '/sahayak',
  '/drishti',
  '/stays',
  '/your-itineraries',
]);

/** Protected nav IDs — the modal fires when these are clicked while logged out */
const PROTECTED_NAV_IDS = new Set(['plan', 'food', 'drishti', 'sahayak', 'itineraries']);

export default function App() {
  const { user, authLoading, logout } = useAuth();

  const [journeyConfig, setJourneyConfig] = useState(() => {
    try {
      const saved = sessionStorage.getItem('np_journey_config');
      if (saved) return JSON.parse(saved);
      const savedItin = sessionStorage.getItem('np_selected_itinerary');
      if (savedItin) {
        const parsed = JSON.parse(savedItin);
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
    } catch {
      return null;
    }
  });

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

  // ID of a saved itinerary to view (bypasses regeneration)
  const [viewingSavedItineraryId, setViewingSavedItineraryId] = useState(null);

  // Login-required modal state
  const [showLoginModal, setShowLoginModal] = useState(false);

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

  // Redirect to landing page if user navigates to a protected path while logged out
  // after the auth check completes.
  useEffect(() => {
    if (!authLoading && !user && PROTECTED_PATHS.has(currentPage)) {
      navigate('/');
      setShowLoginModal(true);
    }
  }, [authLoading, user, currentPage]);

  // Navigate between pages without reloading the application.
  const navigate = useCallback((path) => {
    if (window.location.pathname !== path) {
      window.history.pushState({}, '', path);
    }

    setCurrentPage(path);
    setPanel(null);
    window.scrollTo(0, 0);
  }, []);

  const [journeyResetKey, setJourneyResetKey] = useState(0);

  // End active journey-planning session, clear temporary planning state, and reset to fresh Plan Journey
  const handleFinishJourney = useCallback(() => {
    // 1. Clear journey-related storage keys
    clearJourneyPlanningSession();

    // 2. Clear App-level active journey state
    setJourneyConfig(null);
    setSelectedAttractionIds([]);
    setViewingSavedItineraryId(null);

    // 3. Trigger remount / state reset in planning components
    setJourneyResetKey((k) => k + 1);

    // 4. Navigate to Plan Your Journey
    navigate('/plan-journey');
  }, [navigate]);

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

  /** Guard: attempt to navigate to protected page. Show modal if logged out. */
  const guardedNavigate = useCallback((path, navId) => {
    if (!user) {
      setShowLoginModal(true);
      return false;
    }
    if (path) navigate(path);
    return true;
  }, [user, navigate]);

  const onNav = (id) => {
    setActive(id);

    if (id === 'plan') {
      if (!guardedNavigate('/plan-journey', 'plan')) return;
      return;
    }

    if (id === 'food') {
      if (!guardedNavigate('/food-spots', 'food')) return;
      return;
    }

    if (id === 'drishti') {
      if (!guardedNavigate('/drishti', 'drishti')) return;
      return;
    }

    if (id === 'sahayak') {
      if (!guardedNavigate('/sahayak', 'sahayak')) return;
      return;
    }

    if (id === 'itineraries') {
      if (!guardedNavigate('/your-itineraries', 'itineraries')) return;
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
    if (!guardedNavigate('/food-spots', 'food')) return;
    setActive('food');
  };

  const onCategory = (id) =>
    id === 'food'
      ? openFood()
      : setPanel({ type: 'category', id });

  const close = useCallback(() => setPanel(null), []);

  const onDestination = (id) =>
    setPanel({ type: 'destination', id });

  // ------------------------------------------------------------------
  // Auth loading screen — prevents protected content flashing
  // ------------------------------------------------------------------
  if (authLoading) {
    return (
      <div className="auth-loading-screen">
        <Loader2 size={36} />
        <p>Loading NammaPrayana…</p>
      </div>
    );
  }

  const renderContent = () => {
    // Auth pages (no protection needed)
    if (currentPage === '/login') {
      return (
        <LoginPage
          onBack={() => navigate('/')}
          onSignup={() => navigate('/signup')}
          onSuccess={() => navigate('/')}
        />
      );
    }

    if (currentPage === '/signup') {
      return (
        <SignupPage
          onBack={() => navigate('/')}
          onLogin={() => navigate('/login')}
          onSuccess={() => navigate('/')}
        />
      );
    }

    // ------------------------------------------------------------------
    // Protected pages
    // ------------------------------------------------------------------
    if (currentPage === '/your-itineraries' && user) {
      return (
        <YourItinerariesPage
          onBack={() => navigate('/')}
          onPlanJourney={handleFinishJourney}
          onViewItinerary={(id) => {
            setViewingSavedItineraryId(id);
            navigate('/itinerary');
          }}
        />
      );
    }

    // Page 1: Journey preferences.
    if (currentPage === '/plan-journey' && user) {
      return (
        <PlanJourney
          key={`plan-journey-${journeyResetKey}`}
          resetKey={journeyResetKey}
          onBack={() => navigate('/')}
          onDiveIntoJourney={(preferences) => {
            setJourneyConfig(preferences);
            setViewingSavedItineraryId(null);
            navigate('/route-discovery');
          }}
        />
      );
    }

    // Page 2: Route discovery, transport and tourism itinerary.
    if (currentPage === '/route-discovery' && user) {
      return (
        <RouteDiscoveryPage
          key={`route-discovery-${journeyResetKey}`}
          journeyConfig={journeyConfig}
          onBack={() => navigate('/plan-journey')}
          onGoHome={() => navigate('/')}
          initialDestinations={journeyConfig?.destinations ?? []}
          initialStartDate={journeyConfig?.startDate}
          initialEndDate={journeyConfig?.endDate}
          onContinue={() => navigate('/plan-journey')}
          onOpenStays={() => navigate('/stays')}
          onOpenFood={() => {
            if (!guardedNavigate('/food-spots', 'food')) return;
            setActive('food');
          }}
          onOpenItinerary={(attractionIds) => {
            if (Array.isArray(attractionIds)) {
              setSelectedAttractionIds(attractionIds);
            }
            setViewingSavedItineraryId(null);
            navigate('/itinerary');
          }}
          onOpenSahayak={() => navigate('/sahayak')}
        />
      );
    }

    // Stay page
    if (currentPage === '/stays' && user) {
      return (
        <Stays
          journeyConfig={journeyConfig}
          onBack={() => navigate('/route-discovery')}
        />
      );
    }

    // Page 3: Dedicated Food Spots page.
    if (currentPage === '/food-spots' && user) {
      return (
        <FoodSpots
          onBack={() => navigate('/route-discovery')}
        />
      );
    }

    // Page 4: Itinerary page — supports both new generation and saved view
    if (currentPage === '/itinerary' && user) {
      return (
        <ItineraryPage
          key={`itinerary-${journeyResetKey}`}
          journeyConfig={journeyConfig}
          selectedAttractionIds={selectedAttractionIds}
          savedItineraryId={viewingSavedItineraryId}
          onRequireLogin={() => setShowLoginModal(true)}
          onFinishJourney={handleFinishJourney}
          onBack={() => {
            if (viewingSavedItineraryId) {
              setViewingSavedItineraryId(null);
              navigate('/your-itineraries');
            } else {
              navigate('/route-discovery');
            }
          }}
        />
      );
    }

    // Page 5: Travel Sahayak page
    if (currentPage === '/sahayak' && user) {
      return (
        <SahayakPage
          journeyConfig={journeyConfig}
          onBack={() => navigate('/')}
        />
      );
    }

    // Page 6: Namma Drishti page
    if (currentPage === '/drishti' && user) {
      return (
        <DrishtiPage
          onBack={() => navigate('/')}
        />
      );
    }

    // Default page: Existing landing page.
    return (
      <>
        <a className="skip-link" href="#home">
          Skip to content
        </a>

        <Navbar
          active={active}
          onNav={onNav}
          user={user}
          onLogin={() => navigate('/login')}
          onSignup={() => navigate('/signup')}
          onLogout={async () => { await logout(); navigate('/'); }}
          onYourItineraries={() => onNav('itineraries')}
        />

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
  };

  return (
    <>
      {renderContent()}
      {currentPage !== '/sahayak' && (
        <SahayakFab
          journeyConfig={journeyConfig}
          user={user}
          onRequireLogin={() => setShowLoginModal(true)}
        />
      )}
      {showLoginModal && (
        <LoginRequiredModal
          onLogin={() => { setShowLoginModal(false); navigate('/login'); }}
          onSignup={() => { setShowLoginModal(false); navigate('/signup'); }}
          onClose={() => setShowLoginModal(false)}
        />
      )}
    </>
  );
}