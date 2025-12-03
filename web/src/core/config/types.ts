export interface ModelProvider {
  id: string;
  name: string;
  description: string;
  icon: string;
  models: string[];
  requires_api_key: boolean;
  supports_streaming: boolean;
}

export interface ModelConfig {
  basic: string[];
  reasoning: string[];
}

export interface RagConfig {
  provider: string;
}

export interface DeerFlowConfig {
  rag: RagConfig;
  models: ModelConfig;
  providers?: ModelProvider[];
}
