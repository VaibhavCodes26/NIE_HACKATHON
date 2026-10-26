import React, { useMemo, useState } from "react";
import {
  Hotel,
  Car,
  Utensils,
  ShoppingBag,
  Ticket,
  PieChart,
  Info,
  AlertTriangle,
} from "lucide-react";
import {
  calculateBudgetAllocation,
  formatINR,
  STYLE_METADATA,
} from "../utils/budgetAllocation.js";

const CATEGORY_ICONS = {
  food: Utensils,
  tickets: Ticket,
  travel: Car,
  stays: Hotel,
  shopping: ShoppingBag,
};

export default function BudgetBreakdown({
  totalBudget = 0,
  travelStyle = "comfortable",
  travellerCount = 1,
  estimatedBudget = null,
}) {
  const [activeCategory, setActiveCategory] = useState(null);

  const allocation = useMemo(
    () => calculateBudgetAllocation(totalBudget, travelStyle),
    [totalBudget, travelStyle]
  );

  const styleMeta = STYLE_METADATA[allocation.travelStyle] || STYLE_METADATA.comfortable;

  // Donut geometry: radius = 68, circumference = 2 * PI * 68 ≈ 427.2566
  const radius = 68;
  const circumference = 2 * Math.PI * radius;

  // Precompute stroke dash arrays and offsets
  let accumulatedPercent = 0;
  const slices = allocation.items.map((item) => {
    const dashLength = (circumference * item.percentage) / 100;
    const strokeDasharray = `${dashLength} ${circumference - dashLength}`;
    const strokeDashoffset = -((circumference * accumulatedPercent) / 100);
    accumulatedPercent += item.percentage;
    return {
      ...item,
      icon: CATEGORY_ICONS[item.id] || Hotel,
      strokeDasharray,
      strokeDashoffset,
    };
  });

  const activeItem = activeCategory
    ? slices.find((i) => i.id === activeCategory)
    : null;

  return (
    <article className="itinerary-feature-card itinerary-feature-card--budget-breakdown">
      <div className="itinerary-feature-card__top">
        <span className="itinerary-feature-card__icon itinerary-feature-card__icon--budget">
          <PieChart size={20} />
        </span>
        <div className="itinerary-budget-kicker-wrap">
          <span className="itinerary-feature-card__kicker">
            FINANCIAL CLARITY · {styleMeta.label.toUpperCase()}
          </span>
        </div>
      </div>

      <div className="itinerary-budget-title-area">
        <h3>Your Budget Breakdown</h3>
        <p className="itinerary-budget-subtitle">
          Illustrative allocation for a{" "}
          <strong>{styleMeta.label}</strong> group journey.
        </p>
      </div>

      {allocation.isValid ? (
        <div className="itinerary-budget-body">
          {/* Donut Chart Visualization */}
          <div className="itinerary-donut-wrapper">
            <svg
              className="itinerary-donut-svg"
              viewBox="0 0 200 200"
              width="100%"
              height="200"
              role="img"
              aria-label={`Donut chart showing illustrative budget allocation of ${formatINR(
                allocation.totalBudget
              )} across 5 categories`}
            >
              <defs>
                <filter id="it-donut-shadow" x="-10%" y="-10%" width="120%" height="120%">
                  <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.08" />
                </filter>
              </defs>

              {/* Background track */}
              <circle
                cx="100"
                cy="100"
                r={radius}
                fill="none"
                stroke="#f3ebe0"
                strokeWidth="20"
              />

              {/* Interactive segments */}
              <g transform="rotate(-90 100 100)" filter="url(#it-donut-shadow)">
                {slices.map((slice) => {
                  const isHovered = activeCategory === slice.id;
                  return (
                    <circle
                      key={slice.id}
                      cx="100"
                      cy="100"
                      r={radius}
                      fill="none"
                      stroke={slice.color}
                      strokeWidth={isHovered ? 25 : 20}
                      strokeDasharray={slice.strokeDasharray}
                      strokeDashoffset={slice.strokeDashoffset}
                      className="itinerary-donut-segment"
                      onMouseEnter={() => setActiveCategory(slice.id)}
                      onMouseLeave={() => setActiveCategory(null)}
                      style={{
                        transition: "stroke-width 180ms ease, opacity 180ms ease",
                        opacity: activeCategory && !isHovered ? 0.45 : 1,
                        cursor: "pointer",
                      }}
                    />
                  );
                })}
              </g>

              {/* Donut Center Display */}
              <text
                x="100"
                y="86"
                textAnchor="middle"
                className="itinerary-donut-text-kicker"
              >
                {activeItem ? activeItem.name.toUpperCase() : "TOTAL BUDGET"}
              </text>
              <text
                x="100"
                y="112"
                textAnchor="middle"
                className="itinerary-donut-text-amount"
              >
                {activeItem ? formatINR(activeItem.amount) : formatINR(allocation.totalBudget)}
              </text>
              <text
                x="100"
                y="128"
                textAnchor="middle"
                className="itinerary-donut-text-sub"
              >
                {activeItem
                  ? `${activeItem.percentage}% of budget`
                  : travellerCount > 1
                  ? `${formatINR(allocation.totalBudget / travellerCount)} / traveller`
                  : styleMeta.label}
              </text>
            </svg>
          </div>

          {/* Category Legend & Rupee Values */}
          <div className="itinerary-budget-legend" role="list">
            {slices.map((item) => {
              const IconComp = item.icon;
              const isHovered = activeCategory === item.id;
              return (
                <div
                  key={item.id}
                  className={`itinerary-budget-legend__row ${isHovered ? "is-hovered" : ""}`}
                  onMouseEnter={() => setActiveCategory(item.id)}
                  onMouseLeave={() => setActiveCategory(null)}
                  role="listitem"
                  tabIndex={0}
                  aria-label={`${item.name}: ${formatINR(item.amount)}, ${item.percentage} percent`}
                >
                  <div className="itinerary-budget-legend__left">
                    <span
                      className="itinerary-budget-legend__swatch"
                      style={{ backgroundColor: item.color }}
                      aria-hidden="true"
                    >
                      <IconComp size={12} color="#ffffff" />
                    </span>
                    <span className="itinerary-budget-legend__name">
                      {item.name}
                    </span>
                  </div>

                  <div className="itinerary-budget-legend__right">
                    <span className="itinerary-budget-legend__amount">
                      {formatINR(item.amount)}
                    </span>
                    <span className="itinerary-budget-legend__pct">
                      {item.percentage}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Quick Metrics Bar */}
          <div className="itinerary-budget-quick-stats">
            <div className="itinerary-budget-stat-item">
              <span className="itinerary-budget-stat-label">Group Budget</span>
              <strong className="itinerary-budget-stat-value">
                {formatINR(allocation.totalBudget)}
              </strong>
            </div>
            <div className="itinerary-budget-stat-item">
              <span className="itinerary-budget-stat-label">Per Traveller</span>
              <strong className="itinerary-budget-stat-value">
                {travellerCount > 0
                  ? formatINR(allocation.totalBudget / travellerCount)
                  : "—"}
              </strong>
            </div>
            {estimatedBudget != null && Number(estimatedBudget) > 0 && (
              <div className="itinerary-budget-stat-item">
                <span className="itinerary-budget-stat-label">Activities Est.</span>
                <strong className="itinerary-budget-stat-value">
                  {formatINR(estimatedBudget)}
                </strong>
              </div>
            )}
          </div>

          {totalBudget > 0 && Number(estimatedBudget) > totalBudget && (
            <div className="itinerary-budget-warning">
              <AlertTriangle size={15} />
              <span>Current itinerary activity estimate exceeds your stated budget.</span>
            </div>
          )}

          {/* Mandatory Disclaimer Note */}
          <p className="itinerary-disclaimer itinerary-budget-disclaimer">
            <Info size={13} className="itinerary-disclaimer-icon" />
            <span>
              Illustrative budget allocation. Actual costs may vary depending on
              availability, transport choices, ticket prices, meals, and
              accommodation.
            </span>
          </p>
        </div>
      ) : (
        <div className="itinerary-feature-state itinerary-budget-empty">
          <Info size={18} />
          <p>
            Set your group budget in the planner to view an illustrative spending
            breakdown across stays, food, transport, tickets, and shopping.
          </p>
        </div>
      )}
    </article>
  );
}
