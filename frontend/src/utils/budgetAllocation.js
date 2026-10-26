/**
 * Illustrative budget allocation model for Karnataka journeys.
 * Mutually exclusive categories spanning exactly 100% of the total group budget.
 *
 * Model Assumptions based on regional Karnataka travel patterns:
 * 1. Budget: Prioritizes affordable stays (homestays, dharamshalas, hostels) and transit (KSRTC/trains),
 *    with substantial share for authentic local food (darshinis, regional meals) and key monuments.
 * 2. Comfortable: Balanced allocation for quality 3-star stays, private cabs / self-drive,
 *    varied dining, famous local shopping (Mysuru silk, Channapatna toys), and guided entry passes.
 * 3. Premium: Higher accommodation share for heritage properties, boutique coffee-estate stays,
 *    private vehicle hire, fine regional dining, and artisanal shopping.
 * 4. Ultra-premium: Dominant accommodation share for palace hotels, luxury wellness resorts (Kabini/Coorg),
 *    private chauffeur, curated dining, and bespoke experiences.
 *
 * Exact Rounding Guarantee:
 * Percentages strictly sum to 100%. Rupee amounts for the first 4 categories are rounded,
 * and the residual is allocated to the 5th category to ensure that the
 * displayed rupee amounts always sum to the original group budget.
 */

export const ALLOCATION_PERCENTAGES = {
  budget: {
    stays: 25,
    travel: 25,
    food: 25,
    tickets: 15,
    shopping: 10,
  },
  comfortable: {
    stays: 30,
    travel: 25,
    food: 20,
    shopping: 15,
    tickets: 10,
  },
  premium: {
    stays: 36,
    travel: 22,
    food: 18,
    shopping: 14,
    tickets: 10,
  },
  "ultra-premium": {
    stays: 42,
    travel: 20,
    food: 16,
    shopping: 14,
    tickets: 8,
  },
};

export const STYLE_METADATA = {
  budget: { label: "Budget-Friendly", desc: "Value homestays & local transit" },
  comfortable: { label: "Comfortable", desc: "Balanced comfort & private transit" },
  premium: { label: "Premium", desc: "Heritage stays & dedicated transport" },
  "ultra-premium": { label: "Ultra-Premium", desc: "Luxury resorts & bespoke experiences" },
};

export function normalizeStyle(style) {
  if (!style) return "comfortable";
  const s = String(style).toLowerCase().trim().replace(/[\s_]+/g, "-");
  if (s.includes("ultra") || s.includes("luxury")) return "ultra-premium";
  if (s.includes("prem")) return "premium";
  if (s.includes("budg")) return "budget";
  return "comfortable";
}

export function formatINR(val) {
  const num = Math.round(Number(val) || 0);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(num);
}

/**
 * Calculates an illustrative 5-category budget allocation.
 *
 * @param {number} totalBudget - Total group budget in INR
 * @param {string} travelStyle - "budget" | "comfortable" | "premium" | "ultra-premium"
 * @returns {object} { isValid, totalBudget, travelStyle, items: Array<{ id, name, key, color, pct, amount }> }
 */
export function calculateBudgetAllocation(totalBudget, travelStyle) {
  const rawBudget = Number(totalBudget);
  const isValidBudget = !isNaN(rawBudget) && rawBudget > 0;
  const budget = isValidBudget ? Math.round(rawBudget) : 0;
  const styleKey = normalizeStyle(travelStyle);
  const pcts = ALLOCATION_PERCENTAGES[styleKey] || ALLOCATION_PERCENTAGES.comfortable;

  // 5 required categories
  const categoryDefs = [
    {
      id: "food",
      name: "Food",
      key: "food",
      color: "#d97706", // Turmeric Ochre
      pct: pcts.food,
    },
    {
      id: "tickets",
      name: "Tickets & entry fees",
      key: "tickets",
      color: "#c2410c", // Warm Terracotta
      pct: pcts.tickets,
    },
    {
      id: "travel",
      name: "Travel & local transport",
      key: "travel",
      color: "#15803d", // Karnataka Forest Green
      pct: pcts.travel,
    },
    {
      id: "stays",
      name: "Accommodation / stays",
      key: "stays",
      color: "#801424", // Karnataka Heritage Maroon
      pct: pcts.stays,
    },
    {
      id: "shopping",
      name: "Shopping",
      key: "shopping",
      color: "#7c3aed", // Mysore Silk Purple
      pct: pcts.shopping,
    },
  ];

  if (!isValidBudget) {
    return {
      isValid: false,
      totalBudget: 0,
      travelStyle: styleKey,
      items: categoryDefs.map((c) => ({ ...c, amount: 0, percentage: c.pct })),
    };
  }

  // Calculate integer rupee amounts ensuring exact sum to budget
  let runningSum = 0;
  const items = categoryDefs.map((cat, index) => {
    let amount = 0;
    if (index === categoryDefs.length - 1) {
      amount = Math.max(0, budget - runningSum);
    } else {
      amount = Math.round((budget * cat.pct) / 100);
      runningSum += amount;
    }
    return {
      ...cat,
      amount,
      percentage: cat.pct,
    };
  });

  return {
    isValid: true,
    totalBudget: budget,
    travelStyle: styleKey,
    items,
  };
}
