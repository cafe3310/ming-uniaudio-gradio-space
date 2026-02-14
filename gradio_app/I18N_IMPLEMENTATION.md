# i18n Implementation Documentation

## Overview
This document describes the internationalization (i18n) implementation for the Ming-omni-tts Gradio application, supporting English and Simplified Chinese.

## Features Implemented

### 1. Translation System (`i18n.py`)
- **I18nManager class**: Manages language switching and provides translations
- **TRANSLATIONS dictionary**: Contains all UI text in both English (`en`) and Simplified Chinese (`zh`)
- **Default language**: Chinese (`zh`)
- **Supported languages**: 
  - `en`: English
  - `zh`: Simplified Chinese (简体中文)

### 2. Language Switcher UI
- **Location**: Top-right corner of the header
- **Type**: Radio button selector
- **Options**: "English" and "简体中文"
- **Functionality**: Changes the display language of key UI components

### 3. Translated Components

#### Main Application (`app.py`)
- Main title and subtitle
- Tab names (Ming-omni-tts, Basic Abilities)
- ASR section (title, labels, buttons)
- Edit section (title, labels, buttons, placeholders)
- TTS section (title, labels, buttons, placeholders)
- Examples labels
- Microphone permission accordion

#### Ming-omni-tts Tab (`tab_uniaudio_demo.py`)
- All sub-tabs:
  - Instruct TTS
  - Voice Cloning (Zero-shot TTS)
  - Podcast
  - Speech with BGM
  - Background Music (BGM Generation)
  - Sound Effect Generation (TTA)
- All labels, buttons, dropdowns, and info text
- Status messages

## Technical Implementation

### Language Switching Mechanism
1. User selects language via radio button
2. `change_language()` callback is triggered
3. `I18nManager.set_language()` updates the current language
4. Gradio `gr.update()` refreshes visible Markdown components with new text
5. Main section descriptions update dynamically

### API Value Preservation
**Important**: Only UI display text is translated. All values passed to backend APIs remain unchanged:
- Dropdown values (e.g., "慢速", "中速", "快速" for speed) are displayed with translations but their internal values remain constant
- API call parameters use original values regardless of UI language
- This ensures backend compatibility and prevents breaking changes

## Usage

### For Users
1. Launch the Gradio application
2. Look for the language selector in the top-right corner
3. Select your preferred language ("English" or "简体中文")
4. Key UI sections will update to show text in the selected language

### For Developers

#### Adding New Translations
1. Open `i18n.py`
2. Add new key-value pairs to both `TRANSLATIONS["en"]` and `TRANSLATIONS["zh"]`
3. Use the translation key in your UI code: `self.i18n("your_key")`

Example:
```python
# In i18n.py
TRANSLATIONS = {
    "en": {
        "your_key": "Your English Text",
        ...
    },
    "zh": {
        "your_key": "你的中文文本",
        ...
    }
}

# In your code (app.py or tab_uniaudio_demo.py)
gr.Button(self.i18n("your_key"))
```

#### For Dropdown with Translated Labels but Fixed Values
Use tuples with (label, value) format:
```python
gr.Dropdown(
    [
        (self.i18n("label_key"), "fixed_value"),
        ...
    ],
    value="fixed_value"
)
```

## Testing

### Verified Functionality
- ✅ I18n module imports correctly
- ✅ Translations load for both languages
- ✅ Language switching updates text correctly
- ✅ All UI components render with appropriate language
- ✅ No syntax errors in Python code
- ✅ Core services initialize with i18n support

### Manual Testing Steps
1. Start the application: `python3 app.py`
2. Verify default language (Chinese) displays correctly
3. Click language switcher and select "English"
4. Verify main sections update to English
5. Switch back to "简体中文"
6. Verify text returns to Chinese

## Limitations and Future Improvements

### Current Limitations
1. **Partial Dynamic Update**: Currently, only main section Markdown components update dynamically. Component labels (buttons, textboxes, etc.) set at initialization don't update without page reload.
2. **No Persistence**: Language preference is not saved between sessions.

### Future Improvements
1. **Full Dynamic Updates**: Implement comprehensive component label updates
2. **Language Persistence**: Save language preference in browser localStorage or cookies
3. **More Languages**: Add support for additional languages
4. **URL Parameter**: Support `?lang=en` URL parameter for initial language selection
5. **Gradio i18n Integration**: When Gradio adds built-in i18n support, migrate to use it

## Files Modified
- `gradio_app/i18n.py` (new): Translation system
- `gradio_app/app.py`: Integrated i18n, added language switcher
- `gradio_app/tab_uniaudio_demo.py`: Integrated i18n for all sub-tabs

## Backward Compatibility
The implementation is fully backward compatible:
- No breaking changes to existing functionality
- API calls continue to work with original values
- Default behavior (Chinese UI) matches original implementation
