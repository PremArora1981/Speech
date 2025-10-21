# PRIORITY: Frontend Configuration Management System

**Date:** 2025-10-21
**Status:** 🔴 **Critical Gap - Core Configuration UI Missing**

---

## Executive Summary

The application currently has a **significant gap in frontend configuration capabilities**. While the backend has services for TTS, LLM, and voice management, **the frontend lacks the ability to configure these services dynamically**. Users cannot:

- Select which LLM provider/model to use
- Choose TTS providers (Sarvam vs. ElevenLabs)
- Browse and select voices dynamically from provider APIs
- Access custom/personal voices from their ElevenLabs account
- Configure system prompts for the tele-agent

**This is a critical blocker for production deployment** as users cannot customize their voice agent configuration.

---

## Current State Analysis

### ✅ What Exists

#### Backend
- ✅ TTS orchestrator with Sarvam and ElevenLabs support (`backend/services/tts_service.py`)
- ✅ Static voice registry with hardcoded voices (`backend/utils/voice_registry.py`)
- ✅ LLM service with Sarvam integration (`backend/services/llm_service.py`)
- ✅ Basic system prompt support in LLM service (hardcoded default)
- ✅ WebSocket voice session endpoint (`/api/v1/voice-session`)
- ✅ API authentication system

#### Frontend
- ✅ Basic VoiceSettings component with hardcoded voice catalog (`frontend/src/components/VoiceSettings.tsx`)
- ✅ Language selector component
- ✅ Optimization level slider
- ✅ Analytics dashboard
- ✅ Cost tracking

### ❌ What's Missing

#### Backend APIs (All Missing)
- ❌ **`GET /api/v1/llm/providers`** - List available LLM providers (Sarvam, OpenAI, Anthropic, etc.)
- ❌ **`GET /api/v1/llm/models`** - List available models per provider
- ❌ **`GET /api/v1/tts/providers`** - List available TTS providers
- ❌ **`GET /api/v1/tts/voices`** - Dynamically fetch voices from provider APIs
- ❌ **`GET /api/v1/tts/voices/elevenlabs/custom`** - Fetch user's custom ElevenLabs voices
- ❌ **`GET /api/v1/tts/voices/sarvam`** - Fetch all Sarvam voices from API
- ❌ **`GET /api/v1/tts/voices/preview`** - Preview voice with custom text
- ❌ **`GET /api/v1/system-prompt`** - Get current system prompt
- ❌ **`PUT /api/v1/system-prompt`** - Update system prompt
- ❌ **`GET /api/v1/system-prompt/templates`** - Get system prompt templates
- ❌ **`POST /api/v1/config/session`** - Save session-specific configuration

#### Backend Services (All Missing)
- ❌ **LLM Provider Service** - Manage multiple LLM providers dynamically
- ❌ **Voice Discovery Service** - Fetch voices from provider APIs
- ❌ **System Prompt Manager** - CRUD operations for system prompts
- ❌ **Configuration Service** - Persist and retrieve user/session configurations

#### Frontend Components (All Missing)
- ❌ **LLMProviderSelector** - Select LLM provider and model
- ❌ **TTSProviderSelector** - Select TTS provider
- ❌ **DynamicVoiceGallery** - Fetch and display voices from API
- ❌ **CustomVoiceLibrary** - Display user's custom ElevenLabs voices
- ❌ **SystemPromptEditor** - Rich text editor for system prompt
- ❌ **PromptTemplateLibrary** - Browse and select prompt templates
- ❌ **ConfigurationPanel** - Unified settings management
- ❌ **SessionConfigManager** - Save/load session configurations

---

## Priority Implementation Plan

### 🔴 **PHASE 1: CRITICAL - Backend API Foundation (Week 1)**

**Goal:** Create backend endpoints to support dynamic configuration

#### 1.1 Voice Discovery APIs (Days 1-2)

**Rationale:** Most critical feature - users need to select voices from their ElevenLabs account and see all available Sarvam voices.

**Backend Tasks:**
1. Create `backend/services/voice_discovery.py`:
   - `async def fetch_elevenlabs_voices(api_key: str) -> List[VoiceCapability]`
   - `async def fetch_elevenlabs_custom_voices(api_key: str) -> List[VoiceCapability]`
   - `async def fetch_sarvam_voices() -> List[VoiceCapability]`
   - Cache results with 1-hour TTL

2. Add API endpoints in `backend/api/routes.py`:
   ```python
   @router.get("/tts/providers")
   async def list_tts_providers()

   @router.get("/tts/voices")
   async def list_voices(
       provider: Optional[str] = None,
       language: Optional[str] = None,
       include_custom: bool = True
   )

   @router.get("/tts/voices/elevenlabs/custom")
   async def list_custom_elevenlabs_voices(
       api_key: Optional[str] = None
   )

   @router.post("/tts/voices/preview")
   async def preview_voice(
       voice_id: str,
       provider: str,
       text: str,
       tuning: Optional[VoiceTuning] = None
   )
   ```

3. Update ElevenLabs client (`backend/clients/elevenlabs_tts.py`):
   - Add `async def list_voices(self) -> List[Dict]`
   - Add `async def list_custom_voices(self) -> List[Dict]`
   - Use ElevenLabs API: `GET /v1/voices`

4. Create Sarvam voice discovery (research Sarvam API docs for voice listing endpoint)

**Deliverables:**
- [ ] Voice discovery service
- [ ] Four new API endpoints
- [ ] Enhanced ElevenLabs client
- [ ] Unit tests for voice discovery

---

#### 1.2 LLM Provider APIs (Days 3-4)

**Rationale:** Users need to select which LLM to use (not just hardcoded Sarvam).

**Backend Tasks:**
1. Create `backend/services/llm_provider_registry.py`:
   ```python
   class LLMProviderRegistry:
       def register_provider(provider_name: str, models: List[str])
       def get_providers() -> List[LLMProvider]
       def get_models(provider: str) -> List[LLMModel]
   ```

2. Add LLM provider support:
   - Sarvam (existing)
   - OpenAI (GPT-3.5, GPT-4)
   - Anthropic (Claude)
   - Google (Gemini)
   - Groq (Llama, Mixtral)

3. Add API endpoints:
   ```python
   @router.get("/llm/providers")
   async def list_llm_providers()

   @router.get("/llm/models")
   async def list_llm_models(provider: str)
   ```

4. Update LLM service to support multiple providers:
   - Abstract provider interface
   - Provider-specific clients
   - Unified response format

**Deliverables:**
- [ ] LLM provider registry
- [ ] Multi-provider LLM service
- [ ] Two new API endpoints
- [ ] Provider client abstractions

---

#### 1.3 System Prompt Management (Days 5-6)

**Rationale:** Critical for customizing tele-agent behavior.

**Backend Tasks:**
1. Create database model (`backend/database/models.py`):
   ```python
   class SystemPrompt(Base):
       id: str
       name: str
       prompt_text: str
       category: str  # customer_support, sales, technical, etc.
       is_default: bool
       created_at: datetime
       updated_at: datetime
   ```

2. Create `backend/services/system_prompt_service.py`:
   - CRUD operations for system prompts
   - Template library management
   - Variable interpolation (e.g., {company_name}, {agent_role})

3. Add API endpoints:
   ```python
   @router.get("/system-prompts")
   async def list_system_prompts(category: Optional[str] = None)

   @router.get("/system-prompts/{id}")
   async def get_system_prompt(id: str)

   @router.post("/system-prompts")
   async def create_system_prompt(prompt: SystemPromptCreate)

   @router.put("/system-prompts/{id}")
   async def update_system_prompt(id: str, prompt: SystemPromptUpdate)

   @router.delete("/system-prompts/{id}")
   async def delete_system_prompt(id: str)

   @router.get("/system-prompts/templates")
   async def list_prompt_templates()
   ```

4. Create default prompt templates:
   - Customer Support Agent
   - Sales Assistant
   - Technical Support
   - Appointment Scheduler
   - General Assistant

**Deliverables:**
- [ ] SystemPrompt database model
- [ ] System prompt service
- [ ] Six new API endpoints
- [ ] Five default prompt templates

---

#### 1.4 Session Configuration Management (Day 7)

**Rationale:** Users need to save and load their preferred configurations.

**Backend Tasks:**
1. Create database model:
   ```python
   class SessionConfiguration(Base):
       id: str
       user_id: Optional[str]
       name: str
       llm_provider: str
       llm_model: str
       tts_provider: str
       tts_voice_id: str
       voice_tuning: dict  # pitch, speed, volume
       system_prompt_id: str
       optimization_level: str
       target_language: str
       created_at: datetime
   ```

2. Add API endpoints:
   ```python
   @router.get("/config/sessions")
   async def list_session_configs()

   @router.post("/config/sessions")
   async def save_session_config(config: SessionConfigCreate)

   @router.put("/config/sessions/{id}")
   async def update_session_config(id: str, config: SessionConfigUpdate)

   @router.get("/config/sessions/{id}")
   async def get_session_config(id: str)
   ```

**Deliverables:**
- [ ] SessionConfiguration database model
- [ ] Four new API endpoints

---

### 🟠 **PHASE 2: HIGH PRIORITY - Frontend Configuration UI (Week 2)**

**Goal:** Build comprehensive configuration interface

#### 2.1 LLM Provider Selector Component (Days 1-2)

**Frontend Tasks:**
1. Create `frontend/src/components/LLMProviderSelector.tsx`:
   ```typescript
   interface LLMConfig {
     provider: string;
     model: string;
   }

   export const LLMProviderSelector: React.FC<{
     value: LLMConfig;
     onChange: (config: LLMConfig) => void;
   }>
   ```

2. Features:
   - Provider dropdown (Sarvam, OpenAI, Anthropic, etc.)
   - Model dropdown (filtered by provider)
   - Model descriptions and pricing info
   - Performance metrics display

3. Create API client functions:
   ```typescript
   // frontend/src/lib/api.ts
   export async function fetchLLMProviders()
   export async function fetchLLMModels(provider: string)
   ```

**Deliverables:**
- [ ] LLMProviderSelector component
- [ ] API client integration
- [ ] Provider/model metadata display

---

#### 2.2 Dynamic Voice Gallery (Days 3-4)

**Frontend Tasks:**
1. Enhance `frontend/src/components/VoiceSettings.tsx`:
   - Replace hardcoded `VOICE_CATALOG` with API fetch
   - Add loading states
   - Add error handling
   - Add "Refresh Voices" button
   - Add "My Custom Voices" section for ElevenLabs

2. Create `frontend/src/hooks/useVoices.ts`:
   ```typescript
   export function useVoices(provider: string) {
     const [voices, setVoices] = useState<Voice[]>([]);
     const [loading, setLoading] = useState(true);
     const [error, setError] = useState<Error | null>(null);

     // Fetch voices on mount and provider change
   }
   ```

3. Add filters and search:
   - Filter by gender
   - Filter by language
   - Search by name/characteristics
   - "Show only my custom voices" toggle

4. Add voice preview with custom text:
   - Text input for custom preview
   - Play button
   - Loading state during synthesis

**Deliverables:**
- [ ] Dynamic voice fetching
- [ ] useVoices hook
- [ ] Custom voice support
- [ ] Enhanced filtering and search

---

#### 2.3 System Prompt Editor (Days 5-6)

**Frontend Tasks:**
1. Create `frontend/src/components/SystemPromptEditor.tsx`:
   ```typescript
   export const SystemPromptEditor: React.FC<{
     value: string;
     onChange: (prompt: string) => void;
     onSave: (prompt: SystemPrompt) => void;
   }>
   ```

2. Features:
   - Rich text editor (or enhanced textarea)
   - Character counter
   - Variable picker (insert {company_name}, {agent_role}, etc.)
   - Preview mode
   - Save as template button
   - Template library sidebar

3. Create `frontend/src/components/PromptTemplateLibrary.tsx`:
   - Grid of template cards
   - Template search
   - Category filter
   - "Load Template" button
   - "Preview" button

4. Add validation:
   - Warn if prompt is too long (>2000 characters)
   - Validate variable syntax
   - Test prompt button (send test message)

**Deliverables:**
- [ ] SystemPromptEditor component
- [ ] PromptTemplateLibrary component
- [ ] Variable insertion
- [ ] Template management

---

#### 2.4 Unified Configuration Panel (Day 7)

**Frontend Tasks:**
1. Create `frontend/src/components/ConfigurationPanel.tsx`:
   - Tab-based navigation:
     - **LLM Settings** (provider, model)
     - **Voice Settings** (provider, voice, tuning)
     - **System Prompt** (editor, templates)
     - **Advanced** (optimization, language, etc.)

2. Features:
   - Save configuration button
   - Load saved configuration dropdown
   - Reset to defaults button
   - Export/import configuration (JSON)

3. Add configuration persistence:
   - Save to backend on change (debounced)
   - Load on mount
   - Session-specific configurations

**Deliverables:**
- [ ] ConfigurationPanel component
- [ ] Tab-based navigation
- [ ] Save/load functionality
- [ ] Export/import

---

### 🟡 **PHASE 3: MEDIUM PRIORITY - Enhanced Features (Week 3)**

#### 3.1 TTS Provider Selector (Days 1-2)

**Frontend Tasks:**
1. Create `frontend/src/components/TTSProviderSelector.tsx`:
   - Provider cards (Sarvam, ElevenLabs)
   - Provider comparison table
   - Pricing information
   - Language support matrix

**Deliverables:**
- [ ] TTSProviderSelector component
- [ ] Provider comparison UI

---

#### 3.2 Voice Tuning Enhancements (Days 3-4)

**Frontend Tasks:**
1. Enhance voice tuning controls:
   - Real-time preview during tuning
   - Preset buttons (e.g., "Energetic", "Calm", "Professional")
   - Waveform visualization
   - A/B comparison (original vs. tuned)

**Deliverables:**
- [ ] Enhanced tuning controls
- [ ] Real-time preview
- [ ] Tuning presets

---

#### 3.3 Configuration Analytics (Days 5-7)

**Frontend Tasks:**
1. Create `frontend/src/components/ConfigurationAnalytics.tsx`:
   - Most used configurations
   - Cost per configuration
   - Performance metrics per configuration
   - Optimization recommendations

**Deliverables:**
- [ ] Configuration analytics component
- [ ] Usage tracking
- [ ] Performance insights

---

## Detailed Implementation TODOs

### Backend Development

#### Voice Discovery Service

```bash
# File: backend/services/voice_discovery.py
```

**Tasks:**
- [ ] **Task 1.1.1:** Create `VoiceDiscoveryService` class
  - [ ] Add `__init__` with provider clients
  - [ ] Add caching mechanism (Redis or in-memory)
  - [ ] Add error handling for API failures

- [ ] **Task 1.1.2:** Implement `fetch_elevenlabs_voices()`
  - [ ] Call ElevenLabs API: `GET /v1/voices`
  - [ ] Parse response to `List[VoiceCapability]`
  - [ ] Cache results for 1 hour
  - [ ] Handle API errors gracefully

- [ ] **Task 1.1.3:** Implement `fetch_elevenlabs_custom_voices()`
  - [ ] Use user's API key (from request header or settings)
  - [ ] Call ElevenLabs API: `GET /v1/voices` with user auth
  - [ ] Filter for custom/cloned voices
  - [ ] Mark voices as "custom" in metadata

- [ ] **Task 1.1.4:** Implement `fetch_sarvam_voices()`
  - [ ] Research Sarvam API documentation for voice listing
  - [ ] If no API exists, use static registry as fallback
  - [ ] Parse response to `List[VoiceCapability]`

- [ ] **Task 1.1.5:** Add voice metadata enrichment
  - [ ] Add "is_custom" field
  - [ ] Add "preview_url" field
  - [ ] Add "accent" and "age" metadata (if available)

---

#### LLM Provider Registry

```bash
# File: backend/services/llm_provider_registry.py
```

**Tasks:**
- [ ] **Task 1.2.1:** Create `LLMProvider` dataclass
  ```python
  @dataclass
  class LLMProvider:
      name: str
      display_name: str
      models: List[str]
      supports_streaming: bool
      base_url: str
      requires_api_key: bool
  ```

- [ ] **Task 1.2.2:** Create `LLMProviderRegistry` class
  - [ ] Singleton pattern
  - [ ] Register Sarvam provider
  - [ ] Register OpenAI provider
  - [ ] Register Anthropic provider
  - [ ] Register Google Gemini provider
  - [ ] Register Groq provider

- [ ] **Task 1.2.3:** Implement provider-specific clients
  - [ ] Create `backend/clients/openai_llm.py`
  - [ ] Create `backend/clients/anthropic_llm.py`
  - [ ] Create `backend/clients/google_llm.py`
  - [ ] Create `backend/clients/groq_llm.py`

- [ ] **Task 1.2.4:** Create unified LLM interface
  ```python
  class BaseLLMClient(ABC):
      @abstractmethod
      async def generate(self, messages, **kwargs) -> LLMResponse
  ```

- [ ] **Task 1.2.5:** Update `LLMService` to use provider registry
  - [ ] Accept `provider` and `model` parameters
  - [ ] Route to appropriate client
  - [ ] Handle provider-specific parameters

---

#### System Prompt Management

```bash
# File: backend/services/system_prompt_service.py
```

**Tasks:**
- [ ] **Task 1.3.1:** Create database migration
  - [ ] Add `system_prompts` table
  - [ ] Run migration: `alembic revision --autogenerate -m "Add system prompts"`

- [ ] **Task 1.3.2:** Create `SystemPromptRepository`
  - [ ] CRUD operations
  - [ ] Search by category
  - [ ] Get default prompt

- [ ] **Task 1.3.3:** Create `SystemPromptService`
  - [ ] Wrapper around repository
  - [ ] Template interpolation logic
  - [ ] Validation logic

- [ ] **Task 1.3.4:** Seed default templates
  - [ ] Customer Support template
  - [ ] Sales Assistant template
  - [ ] Technical Support template
  - [ ] Appointment Scheduler template
  - [ ] General Assistant template

- [ ] **Task 1.3.5:** Add API endpoints
  - [ ] `GET /api/v1/system-prompts`
  - [ ] `POST /api/v1/system-prompts`
  - [ ] `PUT /api/v1/system-prompts/{id}`
  - [ ] `DELETE /api/v1/system-prompts/{id}`
  - [ ] `GET /api/v1/system-prompts/templates`

---

#### Session Configuration Management

```bash
# File: backend/services/session_config_service.py
```

**Tasks:**
- [ ] **Task 1.4.1:** Create database migration
  - [ ] Add `session_configurations` table
  - [ ] Run migration

- [ ] **Task 1.4.2:** Create `SessionConfigRepository`
  - [ ] CRUD operations
  - [ ] List by user
  - [ ] Get default config

- [ ] **Task 1.4.3:** Add API endpoints
  - [ ] `GET /api/v1/config/sessions`
  - [ ] `POST /api/v1/config/sessions`
  - [ ] `PUT /api/v1/config/sessions/{id}`
  - [ ] `GET /api/v1/config/sessions/{id}`

- [ ] **Task 1.4.4:** Update voice session WebSocket
  - [ ] Accept `config_id` parameter
  - [ ] Load configuration from database
  - [ ] Apply configuration to pipeline

---

### Frontend Development

#### LLM Provider Selector Component

```bash
# File: frontend/src/components/LLMProviderSelector.tsx
```

**Tasks:**
- [ ] **Task 2.1.1:** Create component structure
  - [ ] Provider dropdown
  - [ ] Model dropdown
  - [ ] Loading states
  - [ ] Error states

- [ ] **Task 2.1.2:** Fetch providers on mount
  - [ ] Call `GET /api/v1/llm/providers`
  - [ ] Store in state
  - [ ] Handle errors

- [ ] **Task 2.1.3:** Fetch models when provider changes
  - [ ] Call `GET /api/v1/llm/models?provider={provider}`
  - [ ] Update model dropdown
  - [ ] Auto-select first model

- [ ] **Task 2.1.4:** Add model metadata display
  - [ ] Model description
  - [ ] Pricing (if available)
  - [ ] Performance tier
  - [ ] Context window size

- [ ] **Task 2.1.5:** Add to ConfigurationPanel
  - [ ] Create "LLM Settings" tab
  - [ ] Wire up to parent state

---

#### Dynamic Voice Gallery

```bash
# File: frontend/src/components/VoiceSettings.tsx (enhancement)
```

**Tasks:**
- [ ] **Task 2.2.1:** Create `useVoices` hook
  ```typescript
  export function useVoices(provider: string, includeCustom: boolean) {
    // Fetch voices from API
    // Cache in React Query
    // Return { voices, loading, error, refetch }
  }
  ```

- [ ] **Task 2.2.2:** Replace hardcoded catalog
  - [ ] Remove `VOICE_CATALOG` constant
  - [ ] Use `useVoices` hook
  - [ ] Add loading skeleton
  - [ ] Add error message

- [ ] **Task 2.2.3:** Add "My Custom Voices" section
  - [ ] Separate section for custom voices
  - [ ] Special badge/icon for custom voices
  - [ ] Only show for ElevenLabs provider

- [ ] **Task 2.2.4:** Add filters
  - [ ] Gender filter (male/female/neutral)
  - [ ] Language filter
  - [ ] Characteristics filter
  - [ ] Search input

- [ ] **Task 2.2.5:** Add "Refresh Voices" button
  - [ ] Call `refetch()` from hook
  - [ ] Show loading state
  - [ ] Show success message

- [ ] **Task 2.2.6:** Enhance voice preview
  - [ ] Custom text input
  - [ ] Apply tuning to preview
  - [ ] Loading state
  - [ ] Error handling

---

#### System Prompt Editor

```bash
# File: frontend/src/components/SystemPromptEditor.tsx
```

**Tasks:**
- [ ] **Task 2.3.1:** Create basic editor
  - [ ] Large textarea (resizable)
  - [ ] Character counter
  - [ ] Syntax highlighting (optional)

- [ ] **Task 2.3.2:** Add variable insertion
  - [ ] Variable picker dropdown
  - [ ] Insert at cursor position
  - [ ] Highlight variables in text

- [ ] **Task 2.3.3:** Add validation
  - [ ] Max length (2000 characters)
  - [ ] Variable syntax check
  - [ ] Show validation errors

- [ ] **Task 2.3.4:** Add preview mode
  - [ ] Toggle between edit and preview
  - [ ] Render with sample variable values
  - [ ] Show formatted output

- [ ] **Task 2.3.5:** Add save functionality
  - [ ] Save button
  - [ ] Name input
  - [ ] Category selector
  - [ ] Call API to save

---

#### Prompt Template Library

```bash
# File: frontend/src/components/PromptTemplateLibrary.tsx
```

**Tasks:**
- [ ] **Task 2.3.6:** Create template library component
  - [ ] Fetch templates from API
  - [ ] Display as grid of cards
  - [ ] Show template name, category, preview

- [ ] **Task 2.3.7:** Add template search
  - [ ] Search input
  - [ ] Filter by name and content
  - [ ] Debounce search

- [ ] **Task 2.3.8:** Add category filter
  - [ ] Category pills
  - [ ] Filter templates by category
  - [ ] "All" option

- [ ] **Task 2.3.9:** Add template actions
  - [ ] "Load Template" button
  - [ ] "Preview" button (modal)
  - [ ] "Edit" button (for custom templates)
  - [ ] "Delete" button (for custom templates)

---

#### Unified Configuration Panel

```bash
# File: frontend/src/components/ConfigurationPanel.tsx
```

**Tasks:**
- [ ] **Task 2.4.1:** Create tab structure
  - [ ] Tab bar with 4 tabs
  - [ ] Active tab highlighting
  - [ ] Tab content area

- [ ] **Task 2.4.2:** Build "LLM Settings" tab
  - [ ] Embed LLMProviderSelector
  - [ ] Model description display
  - [ ] Temperature slider
  - [ ] Max tokens input

- [ ] **Task 2.4.3:** Build "Voice Settings" tab
  - [ ] Embed TTSProviderSelector
  - [ ] Embed VoiceSettings
  - [ ] Voice tuning controls

- [ ] **Task 2.4.4:** Build "System Prompt" tab
  - [ ] Embed SystemPromptEditor
  - [ ] Embed PromptTemplateLibrary

- [ ] **Task 2.4.5:** Build "Advanced" tab
  - [ ] Optimization level selector
  - [ ] Language selector
  - [ ] RAG settings
  - [ ] Cache settings

- [ ] **Task 2.4.6:** Add global actions
  - [ ] Save configuration button
  - [ ] Load configuration dropdown
  - [ ] Reset to defaults button
  - [ ] Export JSON button
  - [ ] Import JSON button

- [ ] **Task 2.4.7:** Implement save/load
  - [ ] Call `POST /api/v1/config/sessions`
  - [ ] Call `GET /api/v1/config/sessions`
  - [ ] Apply loaded config to all tabs

---

#### API Client Functions

```bash
# File: frontend/src/lib/api.ts
```

**Tasks:**
- [ ] **Task 2.5.1:** Add LLM API functions
  ```typescript
  export async function fetchLLMProviders(): Promise<LLMProvider[]>
  export async function fetchLLMModels(provider: string): Promise<LLMModel[]>
  ```

- [ ] **Task 2.5.2:** Add Voice API functions
  ```typescript
  export async function fetchVoices(provider?: string, language?: string): Promise<Voice[]>
  export async function fetchCustomVoices(): Promise<Voice[]>
  export async function previewVoice(voiceId: string, text: string, tuning?: VoiceTuning): Promise<string>
  ```

- [ ] **Task 2.5.3:** Add System Prompt API functions
  ```typescript
  export async function fetchSystemPrompts(category?: string): Promise<SystemPrompt[]>
  export async function fetchPromptTemplates(): Promise<SystemPrompt[]>
  export async function createSystemPrompt(prompt: SystemPromptCreate): Promise<SystemPrompt>
  export async function updateSystemPrompt(id: string, prompt: SystemPromptUpdate): Promise<SystemPrompt>
  export async function deleteSystemPrompt(id: string): Promise<void>
  ```

- [ ] **Task 2.5.4:** Add Session Config API functions
  ```typescript
  export async function fetchSessionConfigs(): Promise<SessionConfig[]>
  export async function fetchSessionConfig(id: string): Promise<SessionConfig>
  export async function saveSessionConfig(config: SessionConfigCreate): Promise<SessionConfig>
  export async function updateSessionConfig(id: string, config: SessionConfigUpdate): Promise<SessionConfig>
  ```

---

#### Integration with Voice Session

```bash
# File: frontend/src/modules/chat/VoiceChat.tsx
```

**Tasks:**
- [ ] **Task 2.6.1:** Accept configuration prop
  - [ ] Add `config?: SessionConfig` prop
  - [ ] Use config for LLM provider/model
  - [ ] Use config for TTS provider/voice
  - [ ] Use config for system prompt

- [ ] **Task 2.6.2:** Send config in WebSocket messages
  - [ ] Add config to "start" message
  - [ ] Backend uses config to initialize pipeline

---

#### App.tsx Integration

```bash
# File: frontend/src/App.tsx
```

**Tasks:**
- [ ] **Task 2.7.1:** Add ConfigurationPanel to App
  - [ ] Create new section
  - [ ] Collapsible/expandable panel
  - [ ] Settings icon button

- [ ] **Task 2.7.2:** Wire up configuration state
  - [ ] Create `sessionConfig` state
  - [ ] Pass to ConfigurationPanel
  - [ ] Pass to VoiceChat

- [ ] **Task 2.7.3:** Load saved config on mount
  - [ ] Fetch default config
  - [ ] Apply to state
  - [ ] Update UI

---

### Testing & Documentation

#### Backend Testing

**Tasks:**
- [ ] **Task 3.1.1:** Unit tests for Voice Discovery
  - [ ] Test `fetch_elevenlabs_voices()`
  - [ ] Test `fetch_custom_voices()`
  - [ ] Test caching mechanism
  - [ ] Test error handling

- [ ] **Task 3.1.2:** Unit tests for LLM Provider Registry
  - [ ] Test provider registration
  - [ ] Test provider lookup
  - [ ] Test model listing

- [ ] **Task 3.1.3:** Unit tests for System Prompt Service
  - [ ] Test CRUD operations
  - [ ] Test template interpolation
  - [ ] Test validation

- [ ] **Task 3.1.4:** Integration tests for new endpoints
  - [ ] Test all GET endpoints
  - [ ] Test all POST endpoints
  - [ ] Test authentication
  - [ ] Test error responses

---

#### Frontend Testing

**Tasks:**
- [ ] **Task 3.2.1:** Component tests
  - [ ] Test LLMProviderSelector
  - [ ] Test VoiceSettings (dynamic)
  - [ ] Test SystemPromptEditor
  - [ ] Test ConfigurationPanel

- [ ] **Task 3.2.2:** Hook tests
  - [ ] Test useVoices hook
  - [ ] Test API client functions

- [ ] **Task 3.2.3:** E2E tests
  - [ ] Test full configuration flow
  - [ ] Test save/load configuration
  - [ ] Test voice selection and preview
  - [ ] Test system prompt editing

---

#### Documentation

**Tasks:**
- [ ] **Task 3.3.1:** Update API documentation
  - [ ] Document all new endpoints
  - [ ] Add request/response examples
  - [ ] Update OpenAPI spec

- [ ] **Task 3.3.2:** Update CLAUDE.md
  - [ ] Document new services
  - [ ] Document new endpoints
  - [ ] Update architecture diagram

- [ ] **Task 3.3.3:** Create user guide
  - [ ] How to select LLM provider
  - [ ] How to browse and select voices
  - [ ] How to customize system prompt
  - [ ] How to save configurations

- [ ] **Task 3.3.4:** Update README.md
  - [ ] Add screenshots of new UI
  - [ ] Update feature list
  - [ ] Add configuration examples

---

## Dependencies & Prerequisites

### Backend Dependencies
```bash
# Add to requirements.txt (if needed)
# None required - using existing dependencies
```

### Frontend Dependencies
```bash
# Add to frontend/package.json
npm install @radix-ui/react-tabs @radix-ui/react-dialog
npm install @tanstack/react-query
npm install react-markdown  # For prompt preview
```

---

## Success Metrics

### Phase 1 Success Criteria
- [ ] All 15+ backend API endpoints implemented
- [ ] Voice discovery working for both Sarvam and ElevenLabs
- [ ] Custom ElevenLabs voices accessible
- [ ] System prompt CRUD operations functional
- [ ] 100% test coverage for new services

### Phase 2 Success Criteria
- [ ] Users can select LLM provider and model from UI
- [ ] Users can browse and select voices dynamically
- [ ] Users can see their custom ElevenLabs voices
- [ ] Users can edit and save system prompts
- [ ] Users can save and load session configurations

### Phase 3 Success Criteria
- [ ] TTS provider comparison UI complete
- [ ] Voice tuning with real-time preview
- [ ] Configuration analytics dashboard
- [ ] Export/import configuration files

---

## Risk Assessment

### High Risk
- **ElevenLabs API Rate Limits:** Voice fetching may hit rate limits
  - *Mitigation:* Implement aggressive caching, batch requests

- **Sarvam Voice API Availability:** May not have dynamic voice listing API
  - *Mitigation:* Fall back to static registry if API unavailable

### Medium Risk
- **Frontend State Complexity:** Managing multiple configuration states
  - *Mitigation:* Use React Query for server state, Zustand for client state

- **Backward Compatibility:** Existing sessions may break
  - *Mitigation:* Provide default configuration for old sessions

### Low Risk
- **Performance:** Multiple API calls on page load
  - *Mitigation:* Parallel fetching, caching, lazy loading

---

## Timeline Summary

| Phase | Duration | Effort | Priority |
|-------|----------|--------|----------|
| Phase 1: Backend APIs | 7 days | 56 hours | 🔴 Critical |
| Phase 2: Frontend UI | 7 days | 56 hours | 🟠 High |
| Phase 3: Enhanced Features | 7 days | 56 hours | 🟡 Medium |
| **Total** | **21 days** | **168 hours** | |

---

## Next Steps

### Immediate Actions (This Week)
1. ✅ **Review and approve this priority document**
2. 🔴 **Start Phase 1, Task 1.1:** Voice Discovery Service
3. 🔴 **Research Sarvam API documentation** for voice listing endpoint
4. 🔴 **Research ElevenLabs API documentation** for custom voices endpoint
5. 🔴 **Set up database migrations** for SystemPrompt and SessionConfiguration

### Week 1 Goals
- [ ] Complete Voice Discovery Service
- [ ] Complete LLM Provider Registry
- [ ] Complete System Prompt Management
- [ ] Complete Session Configuration Management
- [ ] All backend APIs functional

### Week 2 Goals
- [ ] Complete LLM Provider Selector UI
- [ ] Complete Dynamic Voice Gallery
- [ ] Complete System Prompt Editor
- [ ] Complete Configuration Panel
- [ ] Frontend integration complete

### Week 3 Goals
- [ ] Complete TTS Provider Selector
- [ ] Complete Voice Tuning Enhancements
- [ ] Complete Configuration Analytics
- [ ] Testing and documentation
- [ ] Production deployment

---

## Conclusion

This is a **critical gap** that blocks production readiness. The implementation is **well-scoped and achievable in 3 weeks** with focused development. Prioritize Phase 1 (backend) first, as it unblocks Phase 2 (frontend).

**Recommendation:** Start immediately with Voice Discovery Service (Task 1.1), as this is the most user-facing feature and has the highest impact.
