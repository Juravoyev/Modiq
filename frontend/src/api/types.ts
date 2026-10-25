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
  cost_total?: string;
  gross_profit?: string;
}
