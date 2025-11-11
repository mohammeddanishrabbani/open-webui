# Test Plan: Automatic Temporary Chat for DISABLE_CHAT_HISTORY_MODELS

## Feature Overview
When a model is configured in `DISABLE_CHAT_HISTORY_MODELS`, selecting that model should automatically enable temporary chat mode.

## Backend Changes Made

1. **Enhanced Main Config Endpoint** (`/api/config`):
   - Added `disabled_chat_history_models` field to the main configuration response
   - Available to all authenticated users without additional API calls
   - Handles both string and array formats of the configuration

2. **Existing Admin Endpoints** (unchanged):
   - The existing `/api/chats/config/disable-history` endpoints for admin configuration remain unchanged

## Frontend Changes Made

1. **New Store** (`src/lib/stores/index.ts`):
   - `disabledChatHistoryModels` - Reactive store to track the disabled models list

2. **Chat Component Logic** (`src/lib/components/chat/Chat.svelte`):
   - Loads disabled history models from main config when available
   - Reactive statement monitors model selection
   - Automatically enables temporary chat when disabled model is selected
   - Shows notification to user when automatic temporary chat is enabled

## How It Works

1. **On Page Load**:
   - Main config is loaded (including disabled_chat_history_models)
   - Chat component automatically picks up the disabled models from config
   - Stores this list in the `disabledChatHistoryModels` reactive store

2. **On Model Selection**:
   - Reactive statement checks if any selected model is in the disabled list
   - If a disabled model is selected and temporary chat is not already enabled:
     - Automatically enables temporary chat mode
     - Shows toast notification to inform the user

3. **User Experience**:
   - User selects a model that has chat history disabled
   - Chat automatically switches to temporary mode
   - User sees notification: "Temporary chat enabled - selected model has chat history disabled"
   - Chat UI shows temporary chat indicators (dashed borders, eye-slash icon)

## Implementation Details

### Backend
- Added `disabled_chat_history_models` to `/api/config` response in `main.py`
- No authentication issues since it uses existing config endpoint
- Configuration is loaded from `DISABLE_CHAT_HISTORY_MODELS.value`

### Frontend
- Uses existing config system (no new API calls)
- Reactive statement monitors config changes
- Automatic temporary chat activation on model selection
- User notification for transparency

## Testing Steps

1. **Configure a model to disable history**:
   - Go to Admin Settings > Chat History Configuration
   - Add a model ID to DISABLE_CHAT_HISTORY_MODELS
   - Or set environment variable: `DISABLE_CHAT_HISTORY_MODELS='["model-id"]'`

2. **Test automatic temporary chat**:
   - Start a new chat
   - Select the model that has history disabled
   - Verify temporary chat is automatically enabled
   - Verify notification appears

3. **Test normal models**:
   - Select a model not in the disabled list
   - Verify normal chat behavior (no automatic temporary chat)

4. **Test config endpoint**:
   - Call `/api/config` and verify `disabled_chat_history_models` field is present
   - Verify it contains the configured model IDs

## Configuration Examples

### Environment Variable
```bash
DISABLE_CHAT_HISTORY_MODELS='["gpt-4", "claude-3"]'
```

### Admin UI
Models to disable history for:
- gpt-4
- claude-3
- local-model:sensitive

## Benefits

1. **Automatic Compliance**: Users can't accidentally save chat history for sensitive models
2. **Clear Communication**: Users are informed why temporary chat was enabled
3. **Seamless UX**: No additional user action required
4. **No Authentication Issues**: Uses existing config system
5. **Admin Control**: Administrators can configure which models should not store history

## Fixed Issues

- **Authentication Error**: Resolved by using main config endpoint instead of separate authenticated endpoint
- **Timing Issues**: Config is loaded early in app lifecycle, no race conditions
- **Clean Implementation**: Leverages existing systems, minimal new code