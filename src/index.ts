import dotenv from 'dotenv';
dotenv.config();
import { z } from 'zod';

/**
 * Supported embedding model providers
 */
export enum EmbeddingModelProvider {
  OPENAI = 'OpenAI',
  HUGGINGFACE = 'HuggingFace',
  OLLAMA = 'Ollama',
  GOOGLE = 'Google',
  AZURE_OPENAI = 'AzureOpenAI',
  OPENROUTER = 'OpenRouter'
}

/**
 * Base configuration for all embedding models
 */
export interface BaseEmbeddingModelConfig {
  provider: EmbeddingModelProvider;
  modelName: string;
  dimensions?: number;
  maxInputLength?: number;
  apiKey?: string;
}

/**
 * OpenAI embedding model configuration
 */
export interface OpenAIEmbeddingConfig extends BaseEmbeddingModelConfig {
  provider: EmbeddingModelProvider.OPENAI;
  modelName: string;
  dimensions: number;
  maxInputLength: number;
  apiKey?: string;
}

/**
 * HuggingFace embedding model configuration
 */
export interface HuggingFaceEmbeddingConfig extends BaseEmbeddingModelConfig {
  provider: EmbeddingModelProvider.HUGGINGFACE;
  modelName: string;
  dimensions?: number;
  maxInputLength?: number;
}

/**
 * Ollama embedding model configuration
 */
export interface OllamaEmbeddingConfig extends BaseEmbeddingModelConfig {
  provider: EmbeddingModelProvider.OLLAMA;
  modelName: string;
  baseUrl?: string;
  dimensions?: number;
  maxInputLength?: number;
}

/**
 * Google embedding model configuration
 */
export interface GoogleEmbeddingConfig extends BaseEmbeddingModelConfig {
  provider: EmbeddingModelProvider.GOOGLE;
  modelName: string;
  dimensions?: number;
  maxInputLength?: number;
  apiKey?: string;
}

/**
 * Azure OpenAI embedding model configuration
 */
export interface AzureOpenAIEmbeddingConfig extends BaseEmbeddingModelConfig {
  provider: EmbeddingModelProvider.AZURE_OPENAI;
  modelName: string;
  deploymentName: string;
  apiKey?: string;
  azureEndpoint?: string;
  dimensions?: number;
  maxInputLength?: number;
}

/**
 * OpenRouter embedding model configuration
 */
export interface OpenRouterEmbeddingConfig extends BaseEmbeddingModelConfig {
  provider: EmbeddingModelProvider.OPENROUTER;
  modelName: string;
  apiKey?: string;
  baseUrl?: string;
  dimensions?: number;
  maxInputLength?: number;
}

/**
 * Union type for all embedding model configurations
 */
export type EmbeddingModelConfig =
  | OpenAIEmbeddingConfig
  | HuggingFaceEmbeddingConfig
  | OllamaEmbeddingConfig
  | GoogleEmbeddingConfig
  | AzureOpenAIEmbeddingConfig
  | OpenRouterEmbeddingConfig;

/**
 * Zod schema for validating OpenAI embedding configuration
 */
export const OpenAIEmbeddingConfigSchema = z.object({
  provider: z.literal(EmbeddingModelProvider.OPENAI),
  modelName: z.string(),
  dimensions: z.number().optional().default(3072),
  maxInputLength: z.number().optional().default(8191),
  apiKey: z.string().optional()
});

/**
 * Zod schema for validating Ollama embedding configuration
 */
export const OllamaEmbeddingConfigSchema = z.object({
  provider: z.literal(EmbeddingModelProvider.OLLAMA),
  modelName: z.string(),
  baseUrl: z.string().optional(),
  dimensions: z.number().optional(),
  maxInputLength: z.number().optional().default(8192),
});

/**
 * Default OpenAI embedding model configuration
 * Using text-embedding-3-large for superior code understanding capabilities
 */
export const defaultOpenAIEmbeddingConfig: OpenAIEmbeddingConfig = {
  provider: EmbeddingModelProvider.OPENAI,
  modelName: 'text-embedding-3-large',
  dimensions: 3072,
  maxInputLength: 8191,
  apiKey: process.env.OPENAI_API_KEY
};

/**
 * Fallback Ollama embedding model configuration
 * Using nomic-embed-text as a good open-source alternative
 */
export const fallbackOllamaEmbeddingConfig: OllamaEmbeddingConfig = {
  provider: EmbeddingModelProvider.OLLAMA,
  modelName: 'nomic-embed-text',
  baseUrl: process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434',
  maxInputLength: 8192
};

/**
 * Get the appropriate embedding model configuration based on environment
 * Defaults to OpenAI's text-embedding-3-large, falls back to Ollama if no API key
 */
export function getEmbeddingModelConfig(): EmbeddingModelConfig {
  // Check if OpenAI API key is available
  if (process.env.OPENAI_API_KEY) {
    return defaultOpenAIEmbeddingConfig;
  }
  
  // Fall back to Ollama if no OpenAI API key
  return fallbackOllamaEmbeddingConfig;
}

/**
 * IndexingAgent configuration for embedding model
 */
export const embeddingModelConfig = getEmbeddingModelConfig();

export default embeddingModelConfig;
