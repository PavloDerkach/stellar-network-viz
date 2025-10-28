# 🎯 STAGE 2: Extended Filters - Implementation Guide

## 📋 Overview

Stage 2 adds advanced filtering capabilities to complement Stage 1's basic filters:
- **Direction Filter**: Filter by incoming/outgoing transactions
- **Amount Filter**: Filter by transaction amount range

## ✅ What's New in Stage 2

### 1. Direction Filter 📤📥
**Purpose**: Analyze transaction flow direction relative to the main wallet

**Options**:
- **Sent**: Only outgoing transactions from the main wallet
- **Received**: Only incoming transactions to the main wallet
- **All**: Both directions (default)

**Use Cases**:
```
✅ See who my wallet sent money to
✅ See who sent money to my wallet
✅ Analyze spending vs. receiving patterns
✅ Identify transaction direction imbalance
```

### 2. Amount Filter 💰
**Purpose**: Focus on significant or small transactions

**Options**:
- **Min Amount**: Minimum transaction value (e.g., ≥100 XLM)
- **Max Amount**: Maximum transaction value (e.g., ≤10,000 XLM)
- **Range**: Combine both (e.g., 100-10,000 XLM)

**Use Cases**:
```
✅ Find large transactions (whales)
✅ Filter out dust/spam transactions
✅ Analyze specific value ranges
✅ Identify transaction size patterns
```

---

## 🎨 User Interface

### Location: Sidebar → Filters

```
🎯 Filters
├── Filter by asset:        [XLM, USDC, EURC, yUSDC, All]  (Stage 1)
├── Transaction types:      [payment, create_account, ...]  (Stage 1)
├── Enable date filter                                       (Stage 1)
│   ├── From date
│   └── To date
├── Transaction direction:  [Sent, Received, All]           (Stage 2) ⭐ NEW
└── Enable amount filter                                     (Stage 2) ⭐ NEW
    ├── Min amount:         [0.0]
    └── Max amount:         [1000000.0]
```

### Visual Indicators

Active filters are shown in **THREE places**:

1. **During fetch** (spinner):
   ```
   Fetching network data for GDQZZQ...
   (Filters: Assets: USDC, Direction: Sent, Amount: ≥100)
   ```

2. **After fetch** (success message):
   ```
   ✅ Loaded 45 wallets and 123 transactions
   🎯 Active filters: Assets: USDC, Direction: Sent, Amount: ≥100
   ```

3. **Main view** (blue info box):
   ```
   🎯 Active Filters: Assets: USDC | Direction: Sent | Amount: 100-10000
   ```

---

## 💡 Usage Examples

### Example 1: Find Large Outgoing Payments
**Goal**: See where wallet sent large amounts

**Steps**:
1. Transaction direction: Select **"Sent"**
2. Enable amount filter
3. Min amount: **1000**
4. Click "Fetch & Analyze"

**Result**: Only outgoing transactions ≥1000

---

### Example 2: Analyze Small Incoming Transactions
**Goal**: See who sends small payments to wallet

**Steps**:
1. Transaction direction: Select **"Received"**
2. Enable amount filter
3. Min amount: **1**
4. Max amount: **100**
5. Click "Fetch & Analyze"

**Result**: Only incoming transactions between 1-100

---

### Example 3: USDC Whales (Large Senders)
**Goal**: Find who sent large USDC amounts

**Steps**:
1. Filter by asset: Select **"USDC"**
2. Transaction direction: Select **"Received"**
3. Enable amount filter
4. Min amount: **10000**
5. Click "Fetch & Analyze"

**Result**: Large USDC incoming transactions

---

### Example 4: Remove Dust Transactions
**Goal**: Hide spam/dust transactions

**Steps**:
1. Enable amount filter
2. Min amount: **0.1**
3. Click "Fetch & Analyze"

**Result**: All transactions ≥0.1 (removes tiny amounts)

---

## 🔧 Technical Implementation

### Backend Changes

#### 1. stellar_client.py
Added parameters to `fetch_wallet_network()`:

```python
async def fetch_wallet_network(
    self,
    start_wallet: str,
    ...
    direction_filter: Optional[List[str]] = None,  # NEW
    min_amount: Optional[float] = None,            # NEW
    max_amount: Optional[float] = None             # NEW
) -> Dict[str, Any]:
```

#### 2. Direction Filter Logic
```python
# Filter by direction (Sent/Received) relative to start_wallet
if direction_filter and "All" not in direction_filter:
    filtered_by_direction = []
    for tx in filtered_transactions:
        is_sent = (tx.get("from") == start_wallet)
        is_received = (tx.get("to") == start_wallet)
        
        include_tx = False
        if "Sent" in direction_filter and is_sent:
            include_tx = True
        if "Received" in direction_filter and is_received:
            include_tx = True
        
        if include_tx:
            filtered_by_direction.append(tx)
    
    filtered_transactions = filtered_by_direction
```

#### 3. Amount Filter Logic
```python
# Filter by amount
if min_amount is not None or max_amount is not None:
    filtered_by_amount = []
    for tx in filtered_transactions:
        amount = float(tx.get("amount", 0))
        
        if min_amount is not None and amount < min_amount:
            continue
        if max_amount is not None and amount > max_amount:
            continue
        
        filtered_by_amount.append(tx)
    
    filtered_transactions = filtered_by_amount
```

### Frontend Changes

#### 1. app.py - Session State
Added new session state variables:
```python
if "direction_filter" not in st.session_state:
    st.session_state.direction_filter = ["All"]
if "min_amount" not in st.session_state:
    st.session_state.min_amount = None
if "max_amount" not in st.session_state:
    st.session_state.max_amount = None
```

#### 2. app.py - UI Controls
```python
# Direction filter
direction_filter = st.multiselect(
    "Transaction direction:",
    options=["Sent", "Received", "All"],
    default=["All"],
    help="Filter by transaction direction"
)
st.session_state.direction_filter = direction_filter

# Amount filter
use_amount_filter = st.checkbox("Enable amount filter")
if use_amount_filter:
    col1, col2 = st.columns(2)
    with col1:
        min_amount = st.number_input("Min amount:", min_value=0.0)
        st.session_state.min_amount = min_amount
    with col2:
        max_amount = st.number_input("Max amount:", min_value=0.0)
        st.session_state.max_amount = max_amount
```

---

## 🧪 Testing

### Manual Test Cases

#### Test 1: Direction Filter - Sent Only
```
1. Load wallet data
2. Select direction: "Sent" only
3. Fetch data
✅ PASS: Only outgoing transactions shown
✅ PASS: All tx have "from" = main wallet
```

#### Test 2: Direction Filter - Received Only
```
1. Load wallet data
2. Select direction: "Received" only
3. Fetch data
✅ PASS: Only incoming transactions shown
✅ PASS: All tx have "to" = main wallet
```

#### Test 3: Amount Filter - Min Only
```
1. Load wallet data
2. Enable amount filter
3. Set min = 100
4. Fetch data
✅ PASS: All transactions ≥ 100
✅ PASS: No transactions < 100
```

#### Test 4: Amount Filter - Range
```
1. Load wallet data
2. Enable amount filter
3. Set min = 10, max = 1000
4. Fetch data
✅ PASS: All transactions between 10-1000
✅ PASS: No transactions outside range
```

#### Test 5: Combined Filters
```
1. Asset: USDC
2. Direction: Sent
3. Amount: min = 100
4. Fetch data
✅ PASS: Only USDC outgoing ≥100 shown
```

---

## 📊 Filter Combination Matrix

| Stage 1 Filters | Stage 2 Filters | Result |
|----------------|-----------------|--------|
| USDC | Sent, ≥1000 | Large USDC payments out |
| XLM | Received, 1-100 | Small XLM payments in |
| All | Sent | All outgoing transactions |
| payment type | Received, ≥500 | Large incoming payments |
| Oct 1-31 | Sent, 100-1000 | October outgoing 100-1000 |

---

## 🚀 Performance Notes

### Filter Order (Optimized)
```
1. Asset filter       (reduces dataset significantly)
2. Type filter        (further reduces dataset)
3. Date filter        (temporal narrowing)
4. Direction filter   (quick comparison)
5. Amount filter      (numeric comparison)
```

**Why this order?**
- Asset and type filters typically reduce data by 50-80%
- Date filter is moderately expensive (parsing)
- Direction filter is cheap (simple comparison)
- Amount filter is very cheap (numeric comparison)

### Expected Performance
```
Dataset: 10,000 transactions
After asset/type: ~2,000 transactions
After date:       ~500 transactions
After direction:  ~250 transactions
After amount:     ~100-200 transactions
Time: <100ms total filtering
```

---

## 🔮 Future Enhancements

### Potential Stage 2.1 Features
- **Counterparty filter**: Filter by specific wallet addresses
- **Asset issuer filter**: Filter by asset issuer
- **Memo filter**: Search transactions by memo text
- **Fee filter**: Filter by transaction fee range
- **Success filter**: Show only successful/failed transactions

### UI Improvements
- **Filter presets**: Save/load common filter combinations
- **Filter stats**: Show how many tx match before fetching
- **Advanced mode**: Toggle between simple/advanced filters
- **Filter history**: Remember recent filter combinations

---

## 📚 Related Documentation

- **Stage 1**: See `docs/FILTER_SYSTEM.md` for basic filters
- **Stage 3**: See `docs/INTERACTIVITY_FEATURES.md` for graph interactions
- **API**: See `src/api/stellar_client.py` for implementation details

---

## ✅ Verification Checklist

- [x] Direction filter UI added
- [x] Amount filter UI added
- [x] Session state variables added
- [x] Filters passed to API
- [x] Backend logic implemented
- [x] Visual indicators working
- [x] Filter combinations tested
- [x] Documentation created

---

**Stage 2 Status**: ✅ COMPLETE
**Date**: October 26, 2025
**Version**: 2.0.0
