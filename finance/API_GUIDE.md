# Finance API Guide

This document provides a comprehensive guide to the Finance Module APIs, including Accounts, Journals, Ledger, Documents (Credit/Debit Notes), and Reports.

---

## **1. Accounts API**

Manage the Chart of Accounts, including hierarchy, numbering, and status.

### **List Accounts**

`GET /api/finance/account/`

**Filters:**

- `parent_only=true`: List only Root (Level 2) accounts.
- `parent={id}`: List children of a specific parent account.
- `is_posting=true/false`: Filter by posting status.
- `type={type}`: Filter by account type (e.g., `asset`, `liability`).
- `status={active|inactive}`: Filter by status.
- `search={query}`: Search by name or account number.
- `account_number={exact}`: Exact match.
- `opening_balance_min` / `opening_balance_max`: Range filter.
- `created_at__after` / `created_at__before`: Date range filter.

### **Create Account**

`POST /api/finance/account/`

**Payload:**

```json
{
  "account_number": "1.1001",
  "name": "Cash Account",
  "type": "asset",
  "parent_account": 5,
  "is_posting": true,
  "opening_balance": "0.00",
  "status": "active"
}
```

### **Retrieve/Update/Delete**

`GET /api/finance/account/{id}/`
`PUT /api/finance/account/{id}/`
`DELETE /api/finance/account/{id}/`

### **Hierarchy Rules**

- **Level 1 (Type)**: Conceptual, not stored (e.g., 1.0000 Assets).
- **Level 2 (Root)**: Stored in DB, `parent_account=null`, `is_posting=false`. **Must end in '000'** (e.g., 1.1000).
- **Level 3 (Child)**: Stored in DB, has `parent_account`, `is_posting=true`. **Must NOT end in '000'** and must match parent prefix.

---

## **2. Account Number Generator**

Helper API to generate valid next account numbers.

`GET /api/finance/generate-account-number/`

**Parameters:**

- `type={type}`: Required for Level 1/2.
- `level=parent`: Generate next Root number (e.g., 1.2000).
- `parent_account={id}`: Generate next Child number under this parent (e.g., 1.2001).

---

## **3. Journal Entries (Ledger)**

Record financial transactions.

### **List Journal Entries**

`GET /api/finance/journal-entry/`

### **Create Journal Entry**

`POST /api/finance/journal-entry/`

**Payload:**

```json
{
  "type": "journal_voucher",
  "date": "2026-01-30",
  "narration": "Daily Sales",
  "lines": [
    { "account": 10, "debit": "500", "credit": "0" },
    { "account": 20, "debit": "0", "credit": "500" }
  ]
}
```

**Validation:**

- Lines must balance (Total Debit = Total Credit).
- Cannot post to Non-Posting (Root) accounts.

### **Get Journal Lines**

`GET /api/finance/journal-lines/`

- Flat list of all individual debit/credit lines. Supports filtering by date, account, etc.

---

## **4. Documents**

financial documents that automatically create journal entries.

### **Credit Notes**

`GET /api/finance/credit-notes/`
`POST /api/finance/credit-notes/`

**Payload:**

```json
{
  "client": 1,
  "credit_note_number": "CN-001",
  "items": [{ "product": 5, "quantity": 1, "unit_price": 100 }]
}
```

_Automatically creates a Journal Entry._

### **Debit Notes**

`GET /api/finance/debit-notes/`
`POST /api/finance/debit-notes/`

---

## **5. Reports**

Financial statements generated from the ledger.

### **Trial Balance**

`GET /api/finance/trial-balance/?from_date=...&to_date=...`

- Returns grouped balances (Assets, Liabilities, etc.).

### **Profit & Loss**

`GET /api/finance/profit-and-loss/?from_date=...&to_date=...`

- Returns Income vs Expenses and Net Profit.

### **Balance Sheet**

`GET /api/finance/balance-sheet/?from_date=...&to_date=...`

- Returns Assets, Liabilities, and Equity (including Net Profit).

### **Cashflow Statement**

`GET /api/finance/cashflow-statement/?from_date=...&to_date=...`

- Returns Operating, Investing, and Financing activities.

---

## **6. Settings**

Configuration for the finance module.

### **Cashflow Mappings**

`GET /api/finance/cashflow-mappings/`
`POST /api/finance/cashflow-mappings/`

- Map **Posting Accounts** to cashflow categories (Operating, Investing, Financing).

### **Tax Settings**

`GET /api/finance/tax-settings/`

- Manage global tax rates.

### **Number Generator**

`GET /api/finance/generate-number/?type={model_name}`

- Generate sequence numbers for documents.
