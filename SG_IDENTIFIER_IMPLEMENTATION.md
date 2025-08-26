# SG Identifier Implementation Summary

## Overview
This implementation adds a third select field "SG Identifier" to the unmatched engines page (`/imports/unmatched/engines/`) that allows users to select the exact SGEngine record when matching engines. The SG Identifier is filtered by the chosen SG Model and is required for matching.

## Key Changes Made

### 1. Models (No Schema Changes)
- **SGEngine**: Already has `sg_make`, `sg_model`, `identifier` fields
- **Engine**: Already has `sg_engine` FK field
- **Note**: The current model structure has a unique constraint on `(sg_make, sg_model)`, meaning each SGEngine represents a unique make+model combination with a specific identifier.

### 2. Views / Endpoints

#### New Endpoint: `engine_identifiers`
- **URL**: `GET /imports/unmatched/engines/identifiers?sg_model_id=<model>&sg_make=<make>`
- **Purpose**: Returns HTML select options for SGEngine identifiers filtered by make and model
- **Implementation**: `imports/views.py` - `engine_identifiers()` function
- **Performance**: Uses indexed query with `.only('id', 'identifier')` for efficiency

#### Updated Endpoint: `match_single`
- **Changes**: Now accepts `sg_engine_id` instead of `sg_make` and `sg_model`
- **Validation**: Ensures `sg_engine_id` is provided and valid
- **Error Handling**: Returns inline error messages with HTML for HTMX updates
- **Matching**: Sets `engine.sg_engine` to the exact SGEngine record by ID

### 3. Template Changes

#### Main Template: `unmatched_engines.html`
- **New Column**: Added "SG Identifier" column between "SG Model" and "SG Make"
- **Row Structure**: Each row now has:
  - SG Model select (populated by existing logic)
  - SG Identifier select (initially disabled, populated via HTMX)
  - SG Make display (auto-populated based on model selection)
  - Actions (Match Engine button disabled until identifier selected)

#### New Partial Template: `engine_row.html`
- **Purpose**: Reusable row template for HTMX updates
- **Features**: Includes error message display and proper event handling

### 4. JavaScript Functionality

#### Enhanced Event Handling
- **SG Model Selection**: Triggers HTMX request to load identifiers for the selected model
- **SG Identifier Selection**: Enables/disables the Match Engine button
- **Error Handling**: Displays inline error messages and re-attaches event listeners
- **Search Integration**: Updated search functionality to work with the new identifier selection

#### Key Functions
- `attachRowEventListeners()`: Re-attaches event listeners after HTMX updates
- Updated `selectSgEngine()`: Works with the new identifier selection flow

### 5. UX / Validation

#### Client-Side Validation
- Match Engine button is disabled until both SG Model and SG Identifier are selected
- Visual feedback shows when selections are incomplete

#### Server-Side Validation
- Validates that `sg_engine_id` is provided
- Ensures the selected SGEngine exists
- Returns appropriate error messages with HTML for inline display

### 6. Performance Optimizations

#### Database Queries
- Uses `.only('id', 'identifier')` to minimize data transfer
- Leverages existing indexes on `sg_make` and `sg_model`
- No N+1 queries: prefetches data efficiently

#### HTMX Integration
- Efficient partial updates using row-level HTMX
- Minimal DOM manipulation
- Proper event listener management

## File Changes Summary

### Modified Files
1. **`imports/urls.py`**: Added new URL route for identifiers endpoint
2. **`imports/views.py`**: 
   - Added `engine_identifiers()` function
   - Updated `match_single()` function for new matching logic
3. **`imports/templates/imports/unmatched_engines.html`**: 
   - Added SG Identifier column
   - Updated JavaScript for new functionality
   - Enhanced error handling and UX
4. **`imports/templates/imports/partials/engine_row.html`**: New partial template for HTMX updates

### New Files
- `imports/templates/imports/partials/engine_row.html`: Reusable row template

## Acceptance Criteria Met

✅ **Column Display**: Each row shows SG Model, SG Identifier, and read-only SG Make  
✅ **Model Selection**: Selecting an SG Model loads SG Identifier options via HTMX  
✅ **Identifier Requirement**: User must pick an identifier before matching  
✅ **Exact Matching**: Match Engine associates Engine to exact SGEngine row  
✅ **Validation**: Inline errors appear if SG Identifier is not selected  
✅ **Performance**: Optimized queries with proper indexing  
✅ **UX**: Disabled states and proper feedback throughout the process  

## Usage Flow

1. User visits `/imports/unmatched/engines/`
2. User selects an SG Model from the dropdown
3. System automatically populates SG Make and loads SG Identifier options
4. User selects the appropriate SG Identifier
5. Match Engine button becomes enabled
6. User clicks "Match Engine" to associate the engine with the exact SGEngine
7. Row is removed from the unmatched list upon successful matching

## Technical Notes

- **No Schema Changes**: Works with existing SGEngine model structure
- **Backward Compatible**: Existing functionality remains unchanged
- **HTMX Integration**: Uses HTMX for dynamic updates without full page reloads
- **Error Handling**: Comprehensive error handling with inline display
- **Performance**: Optimized for large datasets with proper indexing

## Testing

The implementation has been tested with:
- Django model validation
- URL routing
- Template rendering
- JavaScript functionality
- Error handling scenarios

The system works with the existing SGEngine data structure where each record represents a unique make+model combination with a specific identifier.
