export interface Role {
  id: number;
  name: string;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  role: Role;
  permissions: string[];
}

export interface Brand {
  id: number;
  name: string;
  code: string;
  notes: string | null;
  is_active: boolean;
  is_demo: boolean;
}

export interface Category {
  id: number;
  name: string;
  parent_id: number | null;
  is_active: boolean;
}

export interface Product {
  id: number;
  brand_id: number;
  category_id: number | null;
  name: string;
  model_code: string | null;
  gender: string | null;
  season: string | null;
  collection: string | null;
  description: string | null;
  is_active: boolean;
  is_demo: boolean;
}

export interface ProductVariant {
  id: number;
  product_id: number;
  sku: string;
  barcode: string | null;
  size: string | null;
  color: string | null;
  purchase_cost: number | null;
  mrp: number | null;
  selling_price: number | null;
  reorder_point: number | null;
  minimum_order_quantity: number | null;
  is_active: boolean;
  is_demo: boolean;
}

export interface ProductVariantDetail extends ProductVariant {
  product_name: string;
  brand_name: string;
  category_name: string | null;
  current_stock: number;
}

export interface Warehouse {
  id: number;
  name: string;
  code: string;
  address: string | null;
  is_active: boolean;
  is_demo: boolean;
}

export interface CurrentStockRow {
  variant_id: number;
  sku: string;
  product_name: string;
  brand_name: string;
  warehouse_id: number;
  warehouse_name: string;
  quantity_on_hand: number;
  purchase_cost: number | null;
  selling_price: number | null;
  inventory_cost_value: number;
  inventory_selling_value: number;
}

export interface AgingBucketRow {
  bucket_label: string;
  bucket_min_days: number;
  bucket_max_days: number | null;
  sku_count: number;
  quantity: number;
  inventory_value: number;
}

export interface AgingDetailRow {
  variant_id: number;
  sku: string;
  product_name: string;
  brand_name: string;
  warehouse_name: string;
  batch_id: number;
  batch_code: string;
  received_date: string;
  age_days: number;
  bucket_label: string;
  quantity: number;
  unit_cost: number | null;
  inventory_value: number;
}

export interface DashboardSummary {
  total_skus: number;
  total_units_in_stock: number;
  total_inventory_cost_value: number;
  total_inventory_selling_value: number;
  fast_moving_sku_count: number;
  slow_moving_sku_count: number;
  dead_stock_sku_count: number;
  overdue_stock_count: number;
  upcoming_deadline_count: number;
  open_alert_count: number;
  recent_sales_total_30d: number;
  recent_purchases_total_30d: number;
  data_quality_score: number;
}

export interface Sale {
  id: number;
  invoice_number: string;
  customer_id: number | null;
  warehouse_id: number;
  sale_date: string;
  subtotal: number;
  discount_total: number;
  tax_total: number;
  total: number;
  items: SaleItem[];
}

export interface SaleItem {
  id: number;
  variant_id: number;
  quantity: number;
  unit_price: number;
  unit_cost: number | null;
  discount: number;
  tax: number;
}

export interface Customer {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  gstin: string | null;
  is_active: boolean;
}

export interface Supplier {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  lead_time_days: number | null;
  is_active: boolean;
}

export interface PurchaseOrderItem {
  id: number;
  variant_id: number;
  quantity_ordered: number;
  quantity_received: number;
  unit_cost: number | null;
}

export interface PurchaseOrder {
  id: number;
  po_number: string;
  supplier_id: number;
  warehouse_id: number;
  order_date: string;
  expected_date: string | null;
  status: string;
  items: PurchaseOrderItem[];
}

export interface StockDeadline {
  id: number;
  scope_type: string;
  scope_id: number;
  scope_label: string | null;
  deadline_date: string;
  warning_days: number;
  responsible_user_id: number | null;
  notes: string | null;
  status: string;
  escalation_level: number;
  days_remaining: number | null;
}

export interface Alert {
  id: number;
  alert_type: string;
  severity: string;
  entity_type: string;
  entity_id: number;
  title: string;
  message: string;
  status: string;
  created_at: string;
  resolved_at: string | null;
}

export interface ForecastResult {
  variant_id: number;
  sku: string;
  model_name: string;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  historical_avg_daily_sales: number;
  recent_avg_daily_sales: number;
  forecasts: Record<string, number>;
  mae: number | null;
  rmse: number | null;
  mape: number | null;
  explanation: string;
}

export interface Recommendation {
  id: number;
  variant_id: number;
  sku: string;
  product_name: string;
  brand_name: string;
  generated_at: string;
  recommended_order_qty: number;
  forecast_demand_lead_time: number;
  safety_stock: number;
  current_stock: number;
  incoming_stock: number;
  confidence: string;
  risk_level: string;
  status: string;
  reasoning: Record<string, unknown>;
}

export interface MovementClassificationRow {
  variant_id: number;
  sku: string;
  product_name: string;
  brand_name: string;
  classification: string;
  sales_velocity_per_day: number;
  days_of_cover: number | null;
  current_stock: number;
  explanation: string;
}

export interface StockHealth {
  variant_id: number;
  sku: string;
  score: number;
  status: string;
  factors: { name: string; points: number; max_points: number; detail: string }[];
}

export interface BusinessInsight {
  id: string;
  category: string;
  severity: string;
  text: string;
  supporting_data: Record<string, unknown>;
}

export interface DataQualityReport {
  score: number;
  issue_counts: Record<string, number>;
  issues: Record<string, { entity: string; id: number; label: string }[]>;
}

export interface ImportJob {
  id: number;
  filename: string;
  target_entity: string;
  status: string;
  total_rows: number | null;
  valid_rows: number | null;
  invalid_rows: number | null;
  duplicate_rows: number | null;
  uploaded_at: string;
  committed_at: string | null;
}

export interface AuditLogEntry {
  id: number;
  user_id: number | null;
  action: string;
  entity_type: string;
  entity_id: number | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  reason: string | null;
  created_at: string;
}
