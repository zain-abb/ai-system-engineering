// API Request Types
export interface GenerateRequest {
  prompt: string
  task_type?: 'auto' | 'code_generation' | 'test_generation' | 'code_review' | 'requirements' | 'documentation'
  context?: string
  language?: string
  options?: Record<string, unknown>
}

export interface CodeGenRequest {
  requirements: string
  language?: string
  context?: string
}

export interface TestGenRequest {
  code: string
  language?: string
  framework?: string
}

export interface CodeReviewRequest {
  code: string
  language?: string
  focus?: string
}

export interface IndexRequest {
  directory: string
  extensions?: string[]
}

export interface SearchRequest {
  query: string
  n_results?: number
  language?: string
}

// API Response Types
export interface HealthResponse {
  status: 'healthy' | 'degraded'
  version: string
  agent_ready: boolean
  capabilities: string[]
}

export interface GenerateResponse {
  success: boolean
  result: string
  task_type: string
  confidence: number
  usage: UsageInfo
  error?: string
}

export interface UsageInfo {
  total_tokens?: number
  input_tokens?: number
  output_tokens?: number
  cost?: number
}

export interface CodeGenResponse {
  result: string
  usage: UsageInfo
}

export interface TestGenResponse {
  result: string
  usage: UsageInfo
}

export interface ReviewResponse {
  result: string
  usage: UsageInfo
}

export interface HistoryItem {
  role: string
  content: string
  timestamp: string
  metadata: Record<string, unknown>
}

export interface IndexResponse {
  status: string
  chunks_indexed: number
  directory: string
}

export interface RagStats {
  status?: string
  total_chunks?: number
  indexed_files?: number
}

export interface SearchResult {
  file_path: string
  name: string
  chunk_type: string
  score: number
  content_preview: string
}

export interface SearchResponse {
  query: string
  total_results: number
  results: SearchResult[]
  context: string
}

export interface UsageStats {
  total_requests: number
  total_tokens: number
  input_tokens: number
  output_tokens: number
  total_cost: number
}

// Evaluation Types
export interface EvaluationResult {
  task_id: string
  overall_score: number
  overall_passed: boolean
  results: {
    correctness?: EvalMetric
    robustness?: EvalMetric
    safety?: EvalMetric
    hallucination?: EvalMetric
  }
}

export interface EvalMetric {
  score: number
  passed: boolean
  issues: Issue[]
  details: Record<string, unknown>
}

export interface Issue {
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  location?: string
  suggestion?: string
}
