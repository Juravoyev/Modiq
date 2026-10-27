export type Role = "owner" | "manager" | "cashier";

export interface Branch { id: number; name: string; kind: "store" | "warehouse"; address: string; is_active: boolean }

export interface Me {
  id: number;
  phone: string;
  full_name: string;
  role: Role;
  business: { id: number; name: string; phone: string; address: string; currency: string };
  branches: Branch[];
}

export interface Page<T> { count: number; next: string | null; previous: string | null; results: T[] }

export interface NamedRef { id: number; name: string }
export interface Color extends NamedRef { code: string; hex: string }
export interface Size extends NamedRef { sort_order: number }

export interface Variant {
  id: number;
  product: number;
  product_name: string;
  color: number;
  color_name: string;
  size: number;
  size_name: string;
  sku: string;
  barcode: string;
  purchase_price: string | null;
  sale_price: string | null;
  min_stock: number | null;
  is_active: boolean;
  effective_purchase_price: string;
  effective_sale_price: string;
  effective_min_stock: number;
  stock: number | null;
}

export interface Product {
  id: number;
  name: string;
  article: string;
  category: number | null;
  brand: number | null;
  season: number | null;
  purchase_price: string;
  sale_price: string;
  min_stock: number;
  image: string | null;
  is_active: boolean;
  total_stock: number;
  variants: Variant[];
}

export interface StockRow {
  id: number;
  branch: number;
  branch_name: string;
  variant: number;
  sku: string;
  variant_name: string;
  product: number;
  quantity: number;
  min_stock: number;
  is_low: boolean;
  updated_at: string;
}

export type PaymentType = "cash" | "card" | "online";

export interface SaleLine {
  id: number;
  variant: number;
  sku: string;
  variant_name: string;
  quantity: number;
  unit_price: string;
  discount_amount: string;
  line_total: string;
  below_cost: boolean;
  returned_quantity: number;
}

export interface Sale {
  id: number;
  created_at: string;
  branch: number;
  branch_name: string;
  cashier: number | null;
  cashier_name: string;
  payment_type: PaymentType;
  payment_type_display: string;
  subtotal: string;
  discount_total: string;
  total: string;
  returned_total: string;
  note: string;
  lines: SaleLine[];
  returns: SaleReturn[];
  cost_total?: string;
  gross_profit?: string;
}

export interface SaleReturn { id: number; created_at: string; sale: number; refund_total: string; reason: string;
  lines: { id: number; sale_line: number; sku: string; quantity: number; refund_amount: string }[] }

export type RiskType = "no_sale" | "overstock" | "seasonal" | "restock";
export type RiskLevel = "high" | "medium" | "low";

export interface Risk { type: RiskType; level: RiskLevel; title: string; reason: string; action: string }

export interface VariantInsight {
  stock_id: number;
  branch: number;
  branch_name: string;
  variant: number;
  sku: string;
  variant_name: string;
  product: number;
  product_name: string;
  quantity: number;
  min_stock: number;
  last_sale_at: string | null;
  days_since_last_sale: number | null;
  days_in_stock: number | null;
  sold_in_window: number;
  window_days: number;
  velocity_per_day: number | null;
  days_of_cover: number | null;
  season: string | null;
  risks: Risk[];
  top_level: RiskLevel | null;
}

export interface RiskResponse {
  count: number;
  by_type: Partial<Record<RiskType, number>>;
  by_level: Partial<Record<RiskLevel, number>>;
  results: VariantInsight[];
}

export interface RiskSettings {
  no_sale_days: number;
  sales_window_days: number;
  min_sales_for_velocity: number;
  overstock_cover_days: number;
  season_warning_days: number;
}

export interface Dashboard {
  date: string;
  revenue: string;
  returns_total: string;
  sales_count: number;
  items_sold: number;
  stock_units: number;
  low_stock_count: number;
  risky_count: number;
  gross_profit?: string;
  stock_value?: string;
  low_stock: { sku: string; product_name: string; variant_name: string; branch_name: string; quantity: number; min_stock: number }[];
  alerts: { sku: string; product_name: string; variant_name: string; branch_name: string; type: RiskType; level: RiskLevel; title: string; reason: string }[];
  recent_sales: { id: number; created_at: string; branch_name: string; total: string; items: number }[];
  formulas: Record<string, string>;
}

export type DocStatus = "draft" | "sent" | "received" | "cancelled" | "confirmed" | "applied";

export interface Transfer {
  id: number;
  from_branch: number;
  from_branch_name: string;
  to_branch: number;
  to_branch_name: string;
  status: "draft" | "sent" | "received" | "cancelled";
  note: string;
  lines: { id?: number; variant: number; sku: string; variant_name: string; quantity: number }[];
  created_at: string;
  sent_at: string | null;
  received_at: string | null;
}

export interface StockCount {
  id: number;
  branch: number;
  branch_name: string;
  status: "draft" | "applied" | "cancelled";
  note: string;
  lines: { id?: number; variant: number; sku: string; variant_name: string; counted_quantity: number;
           expected_quantity: number | null; difference: number | null }[];
  shortage: number;
  surplus: number;
  created_at: string;
  applied_at: string | null;
}

export interface Member {
  id: number;
  phone: string;
  full_name: string;
  role: Role;
  branch_ids: number[];
  branch_names: string[];
  is_active: boolean;
}

export type DiscountKind = "percent" | "fixed_price";
export type DiscountState = "draft" | "scheduled" | "active" | "finished" | "cancelled";

export interface Discount {
  id: number;
  variant: number;
  sku: string;
  variant_name: string;
  kind: DiscountKind;
  kind_display: string;
  value: string;
  price_before: string;
  price_after: string;
  unit_cost: string;
  below_cost: boolean;
  starts_on: string;
  ends_on: string;
  status: "draft" | "approved" | "cancelled";
  status_display: string;
  state: DiscountState;
  note: string;
  created_at: string;
  created_by_name: string | null;
  approved_by_name: string | null;
  approved_at: string | null;
  cancelled_at: string | null;
}

export interface ActiveDiscount {
  id: number;
  variant: number;
  price_before: string;
  price_after: string;
  ends_on: string;
}

export interface DiscountPeriod {
  from: string;
  to: string;
  quantity: number;
  revenue: string;
  gross_profit: string;
  per_day: number;
}

export type DiscountResults =
  | { started: false }
  | { started: true; days: number; during: DiscountPeriod; before: DiscountPeriod; note: string };

export interface ReportColumn { key: string; label: string; kind: "text" | "int" | "money" | "pct" }

export interface Report {
  title: string;
  date_from: string | null;
  date_to: string;
  columns: ReportColumn[];
  rows: Record<string, string | number>[];
  totals: Record<string, string | number>;
  formulas: string[];
}

export interface WeekTotals { sales_count: string; items: string; revenue: string; returns: string; gross_profit: string }

export interface WeeklyFacts {
  davr: string;
  shu_hafta: WeekTotals;
  oldingi_hafta: WeekTotals;
  eng_kop_sotilgan: { tovar: string; dona: number; tushum: string }[];
  xavflar_soni: Record<string, number>;
  amaldagi_chegirmalar: number;
}

export interface WeeklySummary {
  facts: WeeklyFacts;
  configured?: boolean;
  text?: string;
  generated_at?: string;
  cached?: boolean;
}
