# 🎯 Filter System Documentation - Stage 1

## Overview

The Stellar Network Visualization tool now includes a fully functional filter system that allows you to narrow down the data displayed in the graph based on various criteria.

## Available Filters

### 1. Asset Filter 💰
**Location**: Sidebar → Filters section
**Purpose**: Show only transactions involving specific assets

**Options**:
- **XLM** - Native Stellar Lumens
- **USDC** - USD Coin (Circle stablecoin)
- **EURC** - Euro Coin
- **yUSDC** - Yield-bearing USDC
- **All** - Show all assets (default)

**How it works**:
- Select one or more assets from the dropdown
- Only transactions involving the selected assets will be fetched and displayed
- If "All" is selected, no asset filtering is applied

**Example**:
- Select only "USDC" → See only USDC transactions
- Select "USDC" and "XLM" → See transactions in either USDC or XLM
- Select "All" → See transactions in any asset

### 2. Transaction Type Filter 📋
**Location**: Sidebar → Filters section
**Purpose**: Show only specific types of transactions

**Options**:
- **payment** - Standard payment transactions
- **create_account** - Account creation transactions
- **path_payment** - Path payment (multi-hop) transactions
- **All** - Show all transaction types (default)

**How it works**:
- Select one or more transaction types from the dropdown
- Only transactions of the selected types will be included
- If "All" is selected, no type filtering is applied

**Example**:
- Select only "payment" → See only payment transactions
- Select "payment" and "create_account" → See both types
- Select "All" → See all transaction types

### 3. Date Range Filter 📅
**Location**: Sidebar → Filters section
**Purpose**: Show only transactions within a specific date range

**How to use**:
1. Check the "Enable date filter" checkbox
2. Select "From date" - transactions after this date
3. Select "To date" - transactions before this date

**How it works**:
- Only transactions within the specified date range are included
- If "Enable date filter" is unchecked, all transactions are included regardless of date
- Default range: Last 30 days

**Example**:
- From: 2025-10-01, To: 2025-10-25 → See only October 2025 transactions
- Uncheck "Enable date filter" → See all transactions regardless of date

## How Filters Work Together

### Filter Combination (AND Logic)
All enabled filters are combined with AND logic, meaning:
- Transaction must match ALL active filters to be included
- Example: If you select "USDC" asset AND "payment" type AND date range "Oct 1-25":
  - ✅ Shows: USDC payment transactions from Oct 1-25
  - ❌ Hides: XLM transactions (wrong asset)
  - ❌ Hides: USDC transactions from September (wrong date)
  - ❌ Hides: USDC create_account transactions (wrong type)

### Performance Impact
- Filters are applied at data fetch time, not after display
- Filtered data loads faster (fewer transactions to process)
- Graph is cleaner with filtered data
- Recommended: Use filters for large networks to improve performance

## Visual Indicators

### Active Filter Display
When filters are active, you'll see:
1. **In sidebar during fetch**: "Fetching network data... (Filters: Assets: USDC, Types: payment)"
2. **Success message**: Shows which filters were applied
3. **Main view**: Blue info box at top showing all active filters
   - Example: "🎯 Active Filters: Assets: USDC | Types: payment | Date range: 2025-10-01 to 2025-10-25"

### No Filters Active
When no filters are active (all set to "All" or disabled):
- No filter indicators shown
- All transactions are included
- Standard success message without filter info

## Common Use Cases

### Use Case 1: Focus on Stablecoin Activity
**Goal**: See only stablecoin (USDC) transactions
**Steps**:
1. Set "Filter by asset" → Select "USDC" only (remove "All")
2. Leave other filters as default
3. Click "Fetch & Analyze"

**Result**: Graph shows only wallets and transactions involving USDC

### Use Case 2: Analyze Recent Payment Activity
**Goal**: See only recent payment transactions
**Steps**:
1. Set "Transaction types" → Select "payment" only
2. Check "Enable date filter"
3. Set "From date" to 7 days ago
4. Click "Fetch & Analyze"

**Result**: Graph shows only payment transactions from the last week

### Use Case 3: Multi-Asset Trading Analysis
**Goal**: See USDC and EURC trading activity
**Steps**:
1. Set "Filter by asset" → Select "USDC" and "EURC" (remove "All")
2. Set "Transaction types" → Select "payment" and "path_payment"
3. Click "Fetch & Analyze"

**Result**: Graph shows wallets trading between USDC and EURC

### Use Case 4: Account Creation Patterns
**Goal**: See how accounts were created
**Steps**:
1. Set "Transaction types" → Select "create_account" only
2. Optionally add date range
3. Click "Fetch & Analyze"

**Result**: Graph shows account creation transactions and patterns

## Tips and Best Practices

### 1. Start Broad, Then Narrow
- First fetch with no filters to see the full network
- Then apply filters to focus on specific aspects
- Compare filtered vs unfiltered views

### 2. Use Filters for Performance
- If network is too large (100+ wallets), apply filters
- Filters reduce data fetched and improve rendering speed
- Recommended for depth > 2 or max_wallets > 50

### 3. Combine Filters Strategically
- Asset + Type: Great for specific trading activity analysis
- Asset + Date: Perfect for trend analysis over time
- Type + Date: Useful for activity pattern discovery

### 4. Reset Filters to See Full Picture
- Set all filters back to "All" to see complete network
- Uncheck "Enable date filter" for all-time view
- Compare filtered vs unfiltered to identify what was excluded

### 5. Check Active Filter Indicator
- Always check the blue info box at the top
- Verify your filters are applied as expected
- Use this to remember which filters are active

## Troubleshooting

### Problem: "No data found" after applying filters
**Cause**: Filters too restrictive, no transactions match
**Solution**: 
- Relax filters (add more assets or types)
- Expand date range
- Check if the wallet actually has transactions matching filters

### Problem: Graph looks the same with and without filters
**Possible causes**:
1. Filters match most transactions anyway (e.g., most transactions are in XLM)
2. Network is small, all transactions match filters
3. Filters not saved properly

**Solution**:
- Check active filter indicator at top
- Try more restrictive filters
- Verify filters are showing in success message

### Problem: Filter not affecting results
**Cause**: Might have selected "All" along with specific options
**Solution**: 
- Remove "All" from multiselect
- Select only specific assets/types you want

### Problem: Date filter showing wrong transactions
**Cause**: Timezone differences or incorrect date format
**Solution**:
- Check dates are in correct format (YYYY-MM-DD)
- Remember dates are inclusive
- Account for timezone (UTC is used)

## Technical Details

### Implementation
- Filters are applied in `src/api/stellar_client.py`
- Method: `fetch_wallet_network()`
- Parameters: `asset_filter`, `tx_type_filter`, `date_from`, `date_to`
- Filtering happens after wallet discovery but before detailed fetch
- This ensures only relevant transactions are processed

### Data Flow
1. User selects filters in sidebar
2. Filters saved to `st.session_state`
3. On "Fetch & Analyze" click, filters passed to API
4. API fetches all wallets in network
5. API filters transactions based on criteria
6. Only matching transactions returned to UI
7. Graph built from filtered data

### Session State Variables
```python
st.session_state.asset_filter      # List[str]
st.session_state.tx_type_filter    # List[str]
st.session_state.date_from         # date | None
st.session_state.date_to           # date | None
```

## Future Enhancements

Potential filter improvements for future versions:
1. **Amount Range**: Filter by transaction volume (min/max)
2. **Direction**: Filter by incoming/outgoing
3. **Counterparty**: Filter by specific wallet addresses
4. **Asset Issuer**: Filter by asset issuer
5. **Memo Filter**: Filter by transaction memo/note
6. **Save Filter Presets**: Save common filter combinations

---

**Last Updated**: October 26, 2025
**Version**: Stage 1 Complete
**Status**: ✅ Fully Functional
