export type Role = "owner" | "manager" | "cashier";

export interface Branch { id: number; name: string; kind: "store" | "warehouse"; address: string; is_active: boolean }

export interface Me {
  id: number;
  phone: string;
  full_name: string;
  role: Role;
  business: { id: number; name: string; phone: string; address: string; currency: string };
  branches: Branch[];
  /** Egasi, menejer yoki egasi huquq bergan sotuvchi. */
  can_approve_returns: boolean;
}

export interface Page<T> { count: number; next: string | null; previous: string | null; results: T[] }

export interface NamedRef { id: number; name: string }
export interface Color extends NamedRef { code: string; hex: string }
export interface Size extends NamedRef { sort_order: number }

export interface Variant {
  id: number;
  product: number;
  product_name: string;
  product_image: string | null;
  color: number;
  color_name: string;
  size: number;
  size_name: string;
  sku: string;
  barcode: string;
  // Tannarx maydonlari faqat egasi va menejerga keladi, kassirda bo'lmaydi.
  purchase_price?: string | null;
  sale_price: string | null;
  min_stock: number | null;
  is_active: boolean;
  effective_purchase_price?: string;
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
  purchase_price?: string;
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
  /** Aksiya chegirmasi (qator bo'yicha jami). */
  auto_discount: string;
  discount_source: DiscountSource;
  discount_label: string;
  promotion: number | null;
  /** Qo'lda berilgan chegirma. */
  discount_amount: string;
  /** Shu qatorga to'g'ri kelgan bonus to'lovi; line_total — pul bilan to'langan qism. */
  bonus_amount: string;
  line_total: string;
  below_cost: boolean;
  /** Qaytarilgan yoki qaytarish tasdig'ini kutayotgan miqdor. */
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
  note: string;
  lines: SaleLine[];
  return_deadline: string;
  customer: number | null;
  customer_info: CustomerBrief | null;
  bonus_spent: string;
  bonus_earned: string;
  cost_total?: string;
  gross_profit?: string;
}

export interface Member {
  id: number;
  phone: string;
  full_name: string;
  role: Role;
  branch_ids: number[];
  can_approve_returns: boolean;
  is_active: boolean;
}

export type TransferStatus = "draft" | "sent" | "received" | "cancelled";

export interface TransferLine { id?: number; variant: number; sku: string; variant_name: string; quantity: number }

export interface Transfer {
  id: number;
  from_branch: number;
  from_branch_name: string;
  to_branch: number;
  to_branch_name: string;
  status: TransferStatus;
  note: string;
  lines: TransferLine[];
  sent_at: string | null;
  received_at: string | null;
  cancelled_at: string | null;
  created_at: string;
}

export type ReturnStatus = "pending" | "approved" | "rejected";

export interface SaleReturn {
  id: number;
  created_at: string;
  sale: number;
  branch: number;
  branch_name: string;
  status: ReturnStatus;
  status_display: string;
  reason: string;
  refund_total: string;
  bonus_refund: string;
  bonus_revoked: string;
  requested_by_name: string;
  decided_by_name: string;
  decided_at: string | null;
  decision_note: string;
  lines: { id: number; sale_line: number; sku: string; variant_name: string; quantity: number; refund_amount: string }[];
  // Faqat menejerga: hisobdan chiqarilgan tannarx (zarar).
  cost_total?: string;
}

export type PromotionKind = "percent" | "amount";
export type PromotionScope = "all" | "category" | "season" | "products";
export type PromotionStatus = "scheduled" | "active" | "ended" | "stopped";

export interface Promotion {
  id: number;
  name: string;
  kind: PromotionKind;
  value: string;
  scope: PromotionScope;
  category: number | null;
  category_name: string | null;
  season: number | null;
  season_name: string | null;
  products: number[];
  product_names: string[];
  starts_on: string;
  ends_on: string;
  is_active: boolean;
  status: PromotionStatus;
  status_display: string;
  label: string;
  source: "manual" | "recommendation";
  created_at: string;
  created_by_name: string;
  sales_count: number;
  units_sold: number;
  discount_given: string;
  /** Aksiya davomida va undan oldingi xuddi shuncha kunda sotilgan dona (boshlanmagan aksiyada null). */
  effect: { days: number; units_during: number; units_before: number } | null;
}

export interface PricingSettings {
  cashier_max_discount_percent: number;
  bonus_enabled: boolean;
  bonus_percent: number;
  bonus_max_share_percent: number;
}

export interface QuoteLine {
  variant: number;
  sku: string;
  quantity: number;
  unit_price: string;
  gross: string;
  auto_discount: string;
  discount_source: DiscountSource;
  discount_label: string;
  promotion: number | null;
  manual_discount: string;
  bonus_amount: string;
  line_total: string;
  below_cost: boolean;
}

/** Kassadagi oldindan hisob: backend savdoni yakunlaganda ham aynan shu qoidalar bilan hisoblaydi. */
export interface Quote {
  customer: CustomerBrief | null;
  lines: QuoteLine[];
  subtotal: string;
  auto_discount_total: string;
  manual_discount_total: string;
  discount_total: string;
  total: string;
  below_cost_skus: string[];
  cashier_max_discount_percent: number;
  bonus: {
    enabled: boolean;
    percent: number;
    max_share_percent: number;
    /** Hozir ishlatish mumkin. */
    available: string;
    /** 24 soatdan keyin ishlatiladi. */
    pending: string;
    /** Shu chekda ko'pi bilan. */
    max: string;
    used: string;
    /** Shu xariddan yig'iladi. */
    earned: string;
  };
}

export type DiscountSource = "" | "promotion" | "privilege";

export interface CustomerGroup { id: number; name: string; discount_percent: number; customers_count: number }

export interface CustomerBrief {
  id: number;
  phone: string;
  full_name: string;
  group_name: string | null;
  discount_percent: number;
}

export interface Customer {
  id: number;
  phone: string;
  full_name: string;
  group: number | null;
  group_name: string | null;
  discount_percent: number;
  note: string;
  created_at: string;
  purchases_count: number;
  total_spent: string;
  bonus_available: string;
  bonus_pending: string;
}

export interface BonusTransaction {
  id: number;
  created_at: string;
  kind: "earn" | "spend" | "refund" | "revoke";
  kind_display: string;
  amount: string;
  sale: number | null;
  sale_return: number | null;
  available_at: string;
}

export type RiskLevel = "high" | "medium" | "low";

export interface Recommendation {
  product_id: number;
  name: string;
  article: string;
  image: string | null;
  category_name: string | null;
  season_name: string | null;
  level: RiskLevel;
  level_display: string;
  /** Tavsiya qilingan chegirma (tannarx chegarasi bilan). */
  discount: number;
  wanted_discount: number;
  safe_discount: number;
  reasons: string[];
  units: number;
  value_cost: string;
  value_retail: string;
  sold_30: number;
  days_since_sale: number | null;
  cover_days: number | null;
  age_days: number;
  last_sale_at: string | null;
  active_promotion: { id: number; label: string } | null;
  can_promote: boolean;
}

export interface RecommendationsResponse {
  summary: { count: number; high: number; medium: number; low: number; frozen_value: string };
  results: Recommendation[];
  ai_configured: boolean;
}

export interface AiSummary { text: string; model: string | null; cached: boolean }

export interface InsightSettings {
  no_sale_days: number;
  high_discount: number;
  cover_days_medium: number;
  medium_discount: number;
  cover_days_low: number;
  low_discount: number;
  season_end_days: number;
  season_discount: number;
  min_age_days: number;
}
