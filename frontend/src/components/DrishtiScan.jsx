import { useState, useRef } from "react";
import { 
  Camera, 
  Upload, 
  Languages, 
  Sparkles, 
  RotateCcw, 
  Copy, 
  Check, 
  AlertCircle, 
  Info,
  Image as ImageIcon
} from "lucide-react";
import "./drishti.css";

const API = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000"
).replace(/\/$/, "");

const TARGET_LANGUAGES = [
  { code: "en", name: "English" },
  { code: "hi", name: "Hindi (हिन्दी)" },
  { code: "mr", name: "Marathi (मराठी)" },
  { code: "ta", name: "Tamil (தமிழ்)" },
  { code: "te", name: "Telugu (తెలుగు)" },
  { code: "ml", name: "Malayalam (മലയാളം)" },
  { code: "bn", name: "Bengali (বাংলা)" },
  { code: "gu", name: "Gujarati (ગુજરાતી)" },
  { code: "kn", name: "Kannada (ಕನ್ನಡ)" },
  { code: "fr", name: "French (Français)" },
  { code: "de", name: "German (Deutsch)" },
  { code: "es", name: "Spanish (Español)" },
];

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB

export default function DrishtiScan({ onBack }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [targetLang, setTargetLang] = useState("en");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isDragActive, setIsDragActive] = useState(false);
  const [copiedField, setCopiedField] = useState("");

  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  // Validate and stage image file
  const handleFileSelection = (file) => {
    setError("");
    setResult(null);

    if (!file) return;

    if (!ALLOWED_TYPES.includes(file.type)) {
      setError("Please select a supported image file (JPEG, PNG, or WebP).");
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setError("Image size exceeds 5MB limit. Please choose a smaller photo.");
      return;
    }

    setSelectedFile(file);

    // Create thumbnail preview URL
    const reader = new FileReader();
    reader.onload = (e) => setPreviewUrl(e.target.result);
    reader.readAsDataURL(file);
  };

  // Drag and Drop handlers
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  // Scan & Translate trigger
  const handleScanAndTranslate = async () => {
    if (!selectedFile) {
      setError("Please select or capture a photograph first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("target_language", targetLang);

      const response = await fetch(`${API}/api/drishti/translate`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error (${response.status})`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message || "Failed to scan and translate image. Please check connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  // Reset to scan another image
  const handleReset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError("");
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (cameraInputRef.current) cameraInputRef.current.value = "";
  };

  // Copy to clipboard helper
  const copyToClipboard = (text, fieldName) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(""), 2000);
  };

  return (
    <div className="drishti-container">
      {/* Hero Header */}
      <div className="drishti-hero">
        <div className="drishti-kannada-lead">ನಮ್ಮ ದೃಷ್ಟಿ</div>
        <h1 className="drishti-title">
          Namma Drishti — <span>See Karnataka in Your Language</span>
        </h1>
        <p className="drishti-desc">
          Capture or upload photographs of Kannada signboards, notices, menus, road directions, 
          and tourist labels to instantly translate them into your chosen language.
        </p>
      </div>

      {/* Main Control Card */}
      <div className="drishti-card">
        {/* Upload & Dropzone Area */}
        {!previewUrl ? (
          <div
            className={`drishti-dropzone ${isDragActive ? "drag-active" : ""}`}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="drishti-drop-icon">
              <Upload />
            </div>
            <p className="drishti-drop-prompt">
              Drag & drop a photo here, or click to browse
            </p>
            <p className="drishti-drop-sub">
              Supports JPEG, PNG, and WebP (up to 5MB)
            </p>

            <div className="drishti-upload-actions" onClick={(e) => e.stopPropagation()}>
              <button
                type="button"
                className="drishti-btn-camera"
                onClick={() => cameraInputRef.current?.click()}
                disabled={loading}
              >
                <Camera size={18} />
                <span>Take Photo</span>
              </button>

              <button
                type="button"
                className="drishti-btn-browse"
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
              >
                <ImageIcon size={18} />
                <span>Select from Gallery</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="drishti-preview-wrapper">
            <img src={previewUrl} alt="Photograph to translate" className="drishti-preview-img" />
            <button
              type="button"
              className="drishti-change-img-btn"
              onClick={handleReset}
              disabled={loading}
            >
              Change Photo
            </button>
          </div>
        )}

        {/* Hidden File Inputs */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          style={{ display: "none" }}
          onChange={(e) => handleFileSelection(e.target.files?.[0])}
        />
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          style={{ display: "none" }}
          onChange={(e) => handleFileSelection(e.target.files?.[0])}
        />

        {/* Language Selection & Action Toolbar */}
        <div className="drishti-toolbar">
          <div className="drishti-lang-group">
            <label htmlFor="target-lang-select" className="drishti-lang-label">
              <Languages size={18} color="#9b1c20" />
              <span>Translate to:</span>
            </label>
            <select
              id="target-lang-select"
              value={targetLang}
              onChange={(e) => setTargetLang(e.target.value)}
              disabled={loading}
              className="drishti-lang-select"
            >
              {TARGET_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="drishti-scan-btn"
            onClick={handleScanAndTranslate}
            disabled={!selectedFile || loading}
          >
            {loading ? (
              <>
                <span className="drishti-spinner" />
                <span>Reading & Translating...</span>
              </>
            ) : (
              <>
                <Sparkles size={18} />
                <span>Scan & Translate</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Message Box */}
      {error && (
        <div className="drishti-error-box" role="alert">
          <AlertCircle size={22} style={{ flexShrink: 0, marginTop: "2px" }} />
          <div>
            <div className="drishti-error-title">Notice</div>
            <div className="drishti-error-msg">{error}</div>
          </div>
        </div>
      )}

      {/* Loading State Animation */}
      {loading && (
        <div className="drishti-loading-box">
          <div className="drishti-loading-pulse">
            <Sparkles size={28} color="#9b1c20" />
          </div>
          <div className="drishti-loading-title">Extracting Kannada Text & Translating</div>
          <p className="drishti-loading-sub">
            Analyzing visual signs, notices, and labels with AI vision...
          </p>
        </div>
      )}

      {/* Result Section */}
      {result && (
        <div className="drishti-results">
          {/* Header Bar */}
          <div className="drishti-res-header">
            <div className="drishti-res-tags">
              <span className="drishti-tag-kind">{result.kind || "Visual Text"}</span>
              {result.cached && (
                <span className="drishti-tag-cached">⚡ Instant Result (Cached)</span>
              )}
            </div>

            <button type="button" className="drishti-rescan-btn" onClick={handleReset}>
              <RotateCcw size={15} />
              <span>Scan Another Photo</span>
            </button>
          </div>

          {/* Unreadable warning if no text found */}
          {!result.success && result.message ? (
            <div className="drishti-unreadable-card">
              <div className="drishti-unreadable-icon">🔍</div>
              <div className="drishti-unreadable-title">No Text Detected</div>
              <p className="drishti-unreadable-msg">{result.message}</p>
              <button type="button" className="drishti-btn-browse" onClick={handleReset}>
                Try another photo
              </button>
            </div>
          ) : (
            <>
              {/* Summary Card */}
              {result.summary && (
                <div className="drishti-summary-card">
                  <div className="drishti-summary-label">Overview</div>
                  <p className="drishti-summary-text">{result.summary}</p>
                </div>
              )}

              {/* Side-by-side or Stacked Dual Text Cards */}
              <div className="drishti-dual-grid">
                {/* Kannada Source Text */}
                <div className="drishti-text-card kannada-card">
                  <div className="drishti-card-top">
                    <h3 className="drishti-card-heading">
                      <span>Detected Kannada Text</span>
                    </h3>
                    {result.detected_text && (
                      <button
                        type="button"
                        className="drishti-copy-btn"
                        onClick={() => copyToClipboard(result.detected_text, "kannada")}
                      >
                        {copiedField === "kannada" ? <Check size={14} color="#1e6d2b" /> : <Copy size={14} />}
                        <span>{copiedField === "kannada" ? "Copied" : "Copy"}</span>
                      </button>
                    )}
                  </div>
                  <p className="drishti-original-content">
                    {result.detected_text || "—"}
                  </p>
                </div>

                {/* Target Translation */}
                <div className="drishti-text-card target-card">
                  <div className="drishti-card-top">
                    <h3 className="drishti-card-heading">
                      <span>Translation ({result.target_language || "Selected Language"})</span>
                    </h3>
                    {result.translated_text && (
                      <button
                        type="button"
                        className="drishti-copy-btn"
                        onClick={() => copyToClipboard(result.translated_text, "translation")}
                      >
                        {copiedField === "translation" ? <Check size={14} color="#1e6d2b" /> : <Copy size={14} />}
                        <span>{copiedField === "translation" ? "Copied" : "Copy"}</span>
                      </button>
                    )}
                  </div>
                  <p className="drishti-target-content">
                    {result.translated_text || "—"}
                  </p>
                </div>
              </div>

              {/* Structured Breakdown Items */}
              {result.items && result.items.length > 0 && (
                <div className="drishti-items-section">
                  <h3 className="drishti-items-title">
                    <Info size={18} color="#9b1c20" />
                    <span>Itemized Breakdown</span>
                  </h3>
                  <div className="drishti-items-grid">
                    {result.items.map((item, idx) => (
                      <div key={idx} className="drishti-item-chip">
                        {item.category && (
                          <div className="drishti-item-chip-cat">{item.category}</div>
                        )}
                        <div className="drishti-item-chip-kn">{item.original}</div>
                        <div className="drishti-item-chip-tr">{item.translation}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          <p className="drishti-disclaimer">
            Translated via AI vision from photo contents. For legal notices, transit schedules, and critical instructions, please verify with local tourism staff.
          </p>
        </div>
      )}
    </div>
  );
}
