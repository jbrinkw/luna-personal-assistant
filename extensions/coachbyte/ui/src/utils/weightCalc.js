// Available plates (number of plates per side)
const AVAILABLE_PLATES = {
  45: 2, // 4x 45lb plates (2 pairs)
  35: 1, // 2x 35lb plates (1 pair)
  25: 1, // 2x 25lb plates (1 pair)
  15: 1, // 2x 15lb plates (1 pair)
  10: 1  // 2x 10lb plates (1 pair)
};

const BAR_WEIGHT = 45;

/**
 * Calculates the closest achievable weight and required plates
 * @param {number} targetWeight - The desired weight in pounds
 * @param {number} maxOverage - Maximum pounds over target allowed (default 5)
 * @returns {{weight: number, plates: number[]}} Actual weight and plates needed (one side)
 */
function calculatePlates(targetWeight, maxOverage = 5) {
  // If target is less than the bar, don't attempt plate calculation
  if (targetWeight < BAR_WEIGHT) {
    return { weight: targetWeight, plates: [] };
  }
  // Subtract bar weight and round to nearest achievable weight
  let remainingWeight = Math.max(0, targetWeight - BAR_WEIGHT) / 2; // Divide by 2 since plates go on both sides
  
  // Try all possible combinations
  let bestCombo = null;
  let minDiff = Infinity;
  
  // Generate all possible combinations of available plates
  function generateCombos(remaining, plates = [], plateTypes = Object.keys(AVAILABLE_PLATES).map(p => parseInt(p)).sort((a,b) => b-a)) {
    // Calculate current weight of this combination
    const currentWeight = plates.reduce((sum, p) => sum + p, 0);
    const totalWeight = (currentWeight * 2) + BAR_WEIGHT;
    const diff = totalWeight - targetWeight;
    
    // If this combination is within our constraints and better than previous best
    if (diff >= 0 && diff <= maxOverage && diff < minDiff) {
      minDiff = diff;
      bestCombo = [...plates];
    }
    
    // Try adding each plate type
    for (const plateWeight of plateTypes) {
      const usedCount = plates.filter(p => p === plateWeight).length;
      if (usedCount < AVAILABLE_PLATES[plateWeight] && 
          currentWeight + plateWeight <= remaining + maxOverage/2) {
        generateCombos(remaining, [...plates, plateWeight], plateTypes.filter(p => p <= plateWeight));
      }
    }
  }
  
  generateCombos(remainingWeight);
  
  if (!bestCombo) {
    // If no valid combination found, return the bar weight
    return { weight: BAR_WEIGHT, plates: [] };
  }
  
  // Calculate actual total weight
  const actualWeight = (bestCombo.reduce((sum, p) => sum + p, 0) * 2) + BAR_WEIGHT;
  
  return {
    weight: actualWeight,
    plates: bestCombo.sort((a,b) => b-a) // Sort plates descending
  };
}

/**
 * Formats weight and plates into a display string
 * @param {number} weight - The total weight
 * @param {number[]} plates - Array of plates needed (one side)
 * @returns {string} Formatted string like "185 (45,25)"
 */
function formatWeightAndPlates(weight, plates) {
  if (plates.length === 0) {
    // Show "bar" instead of 45 when there are no plates
    if (weight === BAR_WEIGHT) return 'bar';
    return `${weight}`;
  }
  return `${weight} (${plates.join(',')})`;
}

export {
  calculatePlates,
  formatWeightAndPlates
}; 