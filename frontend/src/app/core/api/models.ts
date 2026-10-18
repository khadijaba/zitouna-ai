// TypeScript mirror of the backend API. Keep in sync with docs/api-contract.md.

export interface User {
  id: number;
  fullName: string;
  email: string;
  role: 'FARMER' | 'ADMIN';
}

export interface AuthResponse {
  token: string;
  expiresAt: string;
  user: User;
}

export interface Parcel {
  id: number;
  name: string;
  governorate: string;
  latitude: number;
  longitude: number;
  areaHa: number | null;
  treeCount: number | null;
  variety: string | null;
  irrigated: boolean;
  createdAt: string;
}

export type ParcelRequest = Omit<Parcel, 'id' | 'createdAt'>;

/** Every AI result has `mock: true` while the module has no trained model yet. */
interface AiResult {
  mock: boolean;
}

// M1
export interface DiseaseResult extends AiResult {
  label: 'healthy' | 'peacock_spot' | 'aculus_olearius' | 'olive_knot';
  labelFr: string;
  confidence: number;
  probabilities: Record<string, number>;
  advice: string;
  heatmapBase64: string | null;
  modelVersion: string;
  /** true: confidence < 70 %, no diagnosis; `advice` asks to retake the photo. */
  lowConfidence?: boolean | null;
}

// M2
export interface IrrigationResult extends AiResult {
  days: {
    date: string;
    et0Mm: number;
    rainMm: number;
    waterNeedMm: number;
    litersPerTree: number | null;
    irrigate: boolean;
  }[];
  alerts: { date: string; type: 'FROST' | 'HEATWAVE'; severity: 'LOW' | 'MEDIUM' | 'HIGH'; message: string }[];
  modelVersion: string;
}

// M3
export interface YieldResult extends AiResult {
  governorate: string;
  season: number;
  regionalProductionTonnes: number;
  kgPerTree: number | null;
  parcelEstimateKg: number | null;
  parcelLowKg: number | null;
  parcelHighKg: number | null;
  modelVersion: string;
  /** NATIONAL with the trained model: regionalProductionTonnes is then the production of Tunisia. */
  scope?: 'NATIONAL' | 'REGIONAL';
  /** true: production already published by FAOSTAT for this season (not a forecast). */
  observed?: boolean;
}

// M4
export interface PricePoint {
  date: string;
  price: number;
  low: number | null;
  high: number | null;
}

/** history: last observed monthly prices; forecast: one point per week from today (low/high = 80 % interval). */
export interface PriceResult extends AiResult {
  currency: string;
  unit: string;
  history: PricePoint[];
  forecast: PricePoint[];
  recommendation: 'SELL_NOW' | 'STORE';
  reason: string;
  expectedGainTnd: number | null;
  modelVersion: string;
  /** Where the prices come from; null in mock mode. */
  source: string | null;
}

// M5 (through the backend's ChatService)
export type Intent =
  | 'maladie'
  | 'irrigation'
  | 'meteo_alerte'
  | 'recolte'
  | 'prix_vente'
  | 'comptage'
  | 'conseil_general'
  | 'salutation'
  | 'hors_sujet';

export interface ChatRequest {
  text: string;
  parcelId?: number | null;
  /** Set when the farmer clicks a suggestion: the backend skips the classification. */
  forcedIntent?: Intent | null;
}

export interface ChatResponse extends AiResult {
  reply: string;
  intent: Intent;
  /** true: `reply` is a question and `suggestions` should be shown as buttons. */
  clarify: boolean;
  suggestions: Intent[];
  /** Raw result of the module that answered (IrrigationResult, PriceResult...), or null. */
  data: unknown;
  /** "gemini/gemini-3.5-flash" when an LLM wrote the reply, "template" otherwise. */
  generatedBy: string;
}

// M6
export interface TreeCountResult extends AiResult {
  treeCount: number;
  boxes: { x: number; y: number; width: number; height: number; confidence: number }[];
  annotatedImageBase64: string | null;
  modelVersion: string;
}

// M6 -> M3 -> M4
export interface HarvestPlan extends AiResult {
  treeCount: number;
  treeCountSource: 'M6' | 'PARCEL';
  yield: YieldResult;
  estimatedOilKg: number | null;
  price: PriceResult;
  summary: string;
}

export type PredictionType =
  | 'DISEASE'
  | 'IRRIGATION'
  | 'YIELD'
  | 'PRICE'
  | 'CHAT'
  | 'TREE_COUNT'
  | 'HARVEST_PLAN';

export interface PredictionRecord {
  id: number;
  type: PredictionType;
  parcelId: number | null;
  parcelName: string | null;
  request: unknown;
  response: unknown;
  mock: boolean;
  createdAt: string;
}

export interface PageResponse<T> {
  content: T[];
  page: number;
  size: number;
  totalElements: number;
  totalPages: number;
}

// ---- Admin back-office (/api/admin/**, ADMIN role) ----

export interface ModuleStatus {
  id: string;
  name: string;
  type: string;
  up: boolean;
  modelLoaded: boolean | null;
  latencyMs: number | null;
  error: string | null;
}

export interface PlatformStatus {
  application: { name: string; version: string; springBootVersion: string; javaVersion: string; uptimeSeconds: number };
  database: { up: boolean; product: string | null; version: string | null };
  modules: ModuleStatus[];
  checkedAt: string;
}

export interface AdminStats {
  users: number;
  admins: number;
  parcels: number;
  trees: number;
  areaHa: number;
  predictions: number;
  mockPredictions: number;
  predictionsByType: Record<PredictionType, number>;
  last30Days: { date: string; count: number }[];
  parcelsByGovernorate: { governorate: string; parcels: number }[];
  status: PlatformStatus;
}

export interface AdminUser {
  id: number;
  fullName: string;
  email: string;
  role: User['role'];
  createdAt: string;
  parcels: number;
  predictions: number;
}

export interface AdminParcel {
  id: number;
  name: string;
  governorate: string;
  areaHa: number | null;
  treeCount: number | null;
  variety: string | null;
  irrigated: boolean;
  createdAt: string;
  ownerId: number;
  ownerName: string;
  ownerEmail: string;
}

export interface AdminPrediction {
  id: number;
  type: PredictionType;
  mock: boolean;
  createdAt: string;
  userId: number;
  userEmail: string;
  parcelId: number | null;
  parcelName: string | null;
  request: unknown;
  response: unknown;
}
