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
  discount_amount: string;
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
  requested_by_name: string;
  decided_by_name: string;
  decided_at: string | null;
  decision_note: string;
  lines: { id: number; sale_line: number; sku: string; variant_name: string; quantity: number; refund_amount: string }[];
  // Faqat menejerga: hisobdan chiqarilgan tannarx (zarar).
  cost_total?: string;
}
