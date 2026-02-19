/**
 * Unhedged Market ID Extractor
 * Run this script in browser console on https://unhedged.gg
 * It will intercept API calls and extract market IDs
 */

console.log("🔍 Unhedged Market ID Extractor Started");
console.log("📡 Monitoring for market API calls...\n");

// Store found markets
const foundMarkets = new Map();

// Intercept fetch calls
const originalFetch = window.fetch;
window.fetch = async (...args) => {
    const url = args[0];

    // Log all API calls
    if (typeof url === 'string' && url.includes('/api/')) {
        console.log('📡 API Call:', url);

        const response = await originalFetch(...args);

        // Clone response to avoid consuming it
        const clonedResponse = response.clone();

        try {
            const data = await clonedResponse.json();
            console.log('✅ Response:', data);

            // Try to extract market IDs
            extractMarketIds(url, data);
        } catch (e) {
            // Response might not be JSON
        }

        return response;
    }

    return originalFetch(...args);
};

// Extract market IDs from API responses
function extractMarketIds(url, data) {
    // Check if response contains markets
    if (Array.isArray(data)) {
        data.forEach(item => extractFromItem(item));
    } else if (typeof data === 'object') {
        extractFromItem(data);

        // Check for nested data or result fields
        if (data.data) {
            if (Array.isArray(data.data)) {
                data.data.forEach(item => extractFromItem(item));
            } else if (typeof data.data === 'object') {
                extractFromItem(data.data);
            }
        }
        if (data.result) {
            if (Array.isArray(data.result)) {
                data.result.forEach(item => extractFromItem(item));
            } else if (typeof data.result === 'object') {
                extractFromItem(data.result);
            }
        }
    }
}

// Extract market ID from single item
function extractFromItem(item) {
    if (!item || typeof item !== 'object') return;

    // Look for market ID fields
    const idFields = ['id', 'marketId', 'market_id', '_id'];
    const nameFields = ['name', 'title', 'question', 'symbol'];
    const symbolFields = ['symbol', 'ticker', 'pair'];

    let marketId = null;
    let marketName = null;
    let marketSymbol = null;

    for (const field of idFields) {
        if (item[field]) {
            marketId = item[field];
            break;
        }
    }

    for (const field of nameFields) {
        if (item[field]) {
            marketName = item[field];
            break;
        }
    }

    for (const field of symbolFields) {
        if (item[field]) {
            marketSymbol = item[field];
            break;
        }
    }

    // If we found a market ID, try to match it to our symbols
    if (marketId) {
        const name = marketName || marketSymbol || 'Unknown';
        foundMarkets.set(marketId, name);
        console.log(`🎯 Found Market: ${name} (ID: ${marketId})`);
    }
}

// After 10 seconds, print summary and generate config
setTimeout(() => {
    console.log("\n" + "=".repeat(60));
    console.log("📊 SUMMARY - Found Markets");
    console.log("=".repeat(60) + "\n");

    if (foundMarkets.size === 0) {
        console.log("❌ No markets found!");
        console.log("\n💡 Tips:");
        console.log("1. Navigate to the markets page on unhedged.gg");
        console.log("2. Wait for markets to load");
        console.log("3. Run this script again");
        return;
    }

    console.log(`✅ Found ${foundMarkets.size} markets:\n`);

    // Print all found markets
    foundMarkets.forEach((name, id) => {
        console.log(`  - ${name}: ${id}`);
    });

    console.log("\n" + "=".repeat(60));
    console.log("📝 CONFIG.YAML FORMAT");
    console.log("=".repeat(60) + "\n");

    // Try to match markets to our symbols
    const ourSymbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'CCUSDT'];
    const symbolMapping = {};

    foundMarkets.forEach((name, id) => {
        const nameUpper = name.toUpperCase();

        for (const symbol of ourSymbols) {
            const baseSymbol = symbol.replace('USDT', '');
            if (baseSymbol in nameUpper || nameUpper.includes(baseSymbol)) {
                symbolMapping[symbol] = id;
                console.log(`"${symbol}": "${id}"  # Matched from: ${name}`);
            }
        }
    });

    console.log("\n" + "=" .repeat(60));
    console.log("📋 Copy the matching markets above to your config.yaml:");
    console.log("=".repeat(60));
    console.log(`
unhedged:
  api_key: "your_api_key_here"
  enabled: true
  manual_markets:
${Object.entries(symbolMapping).map(([k, v]) => `    "${k}": "${v}"`).join('\n')}
    `);

    // Restore original fetch
    window.fetch = originalFetch;
    console.log("\n✅ Done! Fetch interceptor removed.");

}, 10000);

// Also try to find markets in window object
setTimeout(() => {
    console.log("\n🔍 Searching window object for market data...");

    // Common places where SPA store data
    const searchPaths = [
        '__NUXT__',
        '__SVELTE__',
        'stores',
        'state',
        'markets',
        'app'
    ];

    for (const path of searchPaths) {
        if (window[path]) {
            console.log(`📦 Found window.${path}:`, window[path]);

            // Try to extract market data
            const data = JSON.stringify(window[path]);
            if (data.includes('market') || data.includes('BTC') || data.includes('ETH')) {
                console.log(`✅ Market data likely in window.${path}`);
                console.log("Run this in console to inspect:");
                console.log(`console.log('${path}', window.${path})`);
            }
        }
    }
}, 2000);

console.log("\n💡 Navigate to unhedged.gg markets page to capture market IDs!");
console.log("⏰ Results will be displayed in 10 seconds...\n");
