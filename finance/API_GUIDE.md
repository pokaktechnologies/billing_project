# Finance API Guide - Account & Journal Changes

## Account Endpoints

### Base URL: `/api/finance/account/`

---

## Generate Account Number (New!)

**GET** `/generate-account-number/`

Generate the next account number without saving. Use this for frontend auto-suggestion.

### For Type-level Account (Level 1)

```
GET /generate-account-number/?type=asset
```

**Response:**

```json
{
  "next_number": "10000",
  "level": 1,
  "type": "asset"
}
```

### For Parent Account (Level 2)

```
GET /generate-account-number/?type=asset&level=parent
```

**Response:**

```json
{
  "next_number": "1.1000",
  "level": 2,
  "type": "asset"
}
```

### For Child Account (Level 3)

```
GET /generate-account-number/?parent_account=5
```

**Response:**

```json
{
  "next_number": "1.1001",
  "level": 3,
  "parent_account": "5",
  "parent_number": "1.1000",
  "type": "asset"
}
```

### Parameters

| Parameter        | Required | Description                                                                             |
| ---------------- | -------- | --------------------------------------------------------------------------------------- |
| `type`           | Yes\*    | Account type: asset, liability, equity, sales, cost_of_sales, revenue, general_expenses |
| `level`          | No       | Set to "parent" for Level 2, omit for Level 1                                           |
| `parent_account` | Yes\*    | Parent account ID (for child accounts)                                                  |

\*Either `type` or `parent_account` is required

### Numbering Format

| Level            | Format | Example                |
| ---------------- | ------ | ---------------------- |
| Type (Level 1)   | X0000  | 10000, 20000, 30000    |
| Parent (Level 2) | X.Y000 | 1.1000, 1.2000, 2.1000 |
| Child (Level 3)  | X.Y00Z | 1.1001, 1.1002, 1.2001 |

---

## List/Create Accounts

**GET** `/account/`  
**POST** `/account/`

### Request Body (POST)

```json
{
  "account_number": "1.1001",
  "name": "Cash",
  "type": "asset",
  "parent_account": 2,
  "is_posting": true,
  "opening_balance": "0.00",
  "status": "active"
}
```

### Response

```json
{
  "id": 5,
  "account_number": "1.1001",
  "name": "Cash",
  "type": "asset",
  "parent_account": 2,
  "parent_account_name": "Current Assets",
  "parent_account_number": "1.1000",
  "is_posting": true,
  "opening_balance": "0.00",
  "closing_balance": "5000.00",
  "status": "active",
  "depth": 3,
  "created_at": "2026-01-29T12:00:00Z"
}
```

---

## Retrieve/Update/Delete Account

**GET/PUT/PATCH/DELETE** `/account/{id}/`

---

## Account Number Rules

| Type             | Prefix | Example                |
| ---------------- | ------ | ---------------------- |
| Asset            | 1      | 1.0000, 1.1000, 1.1001 |
| Liability        | 2      | 2.0000, 2.1000         |
| Equity           | 3      | 3.0000, 3.1000         |
| Sales            | 4      | 4.0000, 4.1000         |
| Cost of Sales    | 5      | 5.0000, 5.1000         |
| Revenue          | 6      | 6.0000, 6.1000         |
| General Expenses | 7      | 7.0000, 7.1000         |

---

## Hierarchy Rules

| Level      | Example               | is_posting |
| ---------- | --------------------- | ---------- |
| 1 (Type)   | 1.0000 Assets         | `false`    |
| 2 (Parent) | 1.1000 Current Assets | `false`    |
| 3 (Child)  | 1.1001 Cash           | `true`     |

**Max depth = 3 levels**

---

## Validation Errors

| Error                                           | Cause                            |
| ----------------------------------------------- | -------------------------------- |
| `"Account number must start with 'X' for type"` | Number prefix doesn't match type |
| `"Maximum hierarchy depth is 3 levels"`         | Trying to create 4th level       |
| `"Parent account must be non-posting"`          | Parent has `is_posting=true`     |
| `"Account type must match parent"`              | Child type differs from parent   |

---

## Journal Entry Endpoints

### Base URL: `/api/finance/journal-entry/`

**GET** `/journal-entry/` - List entries  
**POST** `/journal-entry/` - Create entry  
**GET/PUT/DELETE** `/journal-entry/{id}/` - Detail

### Request Body (POST)

```json
{
  "type": "journal_voucher",
  "date": "2026-01-29T12:00:00Z",
  "narration": "Transfer entry",
  "lines": [
    { "account": 5, "debit": "1000.00", "credit": "0.00" },
    { "account": 8, "debit": "0.00", "credit": "1000.00" }
  ]
}
```

### Journal Line Validation

| Rule                | Error                                                |
| ------------------- | ---------------------------------------------------- |
| Non-posting account | `"Cannot post to non-posting account"`               |
| Both debit & credit | `"A line cannot have both debit and credit"`         |
| No amount           | `"Either debit or credit must be greater than zero"` |

---

## Journal Lines Endpoints

**GET** `/journal-lines/` - Flat list of all lines  
**GET** `/journal-lines/{id}/` - Line detail

### Response Fields

```json
{
  "id": 1,
  "account": 5,
  "account_name": "Cash",
  "account_type": "asset",
  "account_is_posting": true,
  "debit": "1000.00",
  "credit": "0.00",
  "voucher_type": "journal_voucher",
  "voucher_number": "JE|100001",
  "date": "2026-01-29",
  "narration": "Transfer entry"
}
```

---

## Balance Calculation

| Account Type                           | Formula                    |
| -------------------------------------- | -------------------------- |
| Asset, Cost of Sales, General Expenses | `opening + debit - credit` |
| Liability, Equity, Sales, Revenue      | `opening + credit - debit` |
