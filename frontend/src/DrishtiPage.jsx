import { ArrowLeft } from "lucide-react";
import DrishtiScan from "./components/DrishtiScan";
import { KaMark, Wordmark } from "./components/Logo";
import "./components/drishti.css";

export default function DrishtiPage({ onBack }) {
  return (
    <div className="drishti-page">
      {/* Top Header */}
      <header className="drishti-header">
        <div className="drishti-header-inner">
          <button 
            type="button" 
            className="drishti-back-btn" 
            onClick={onBack}
            aria-label="Back to home"
          >
            <ArrowLeft size={18} />
            <span>Back</span>
          </button>

          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <KaMark size={28} />
            <Wordmark />
          </div>

          <span className="drishti-badge-kannada">ದೃಷ್ಟಿ</span>
        </div>
      </header>

      {/* Main Drishti Scan Content */}
      <main style={{ flex: 1 }}>
        <DrishtiScan onBack={onBack} />
      </main>
    </div>
  );
}
