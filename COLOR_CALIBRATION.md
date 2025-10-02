# 🎨 Color Calibration Guide - Inky Photo Frame

## Problem: Yellow/Green Tint on E-Ink Display

If your photos appear with a yellow/green tint on the e-ink display, this is usually caused by:
1. **iPhone/P3 color profile** not being converted to sRGB
2. **Over-saturation** making colors too intense
3. **Auto-contrast** shifting color balance

## ✅ v2.0.1 Improvements

### Automatic Fixes
- ✅ **P3 → sRGB conversion**: Photos from iPhone/modern phones are now correctly converted
- ✅ **Reduced saturation**: 0.6 → 0.5 (less intense colors)
- ✅ **Gentler contrast**: cutoff 2 → 1 (preserves original colors better)

### Manual Adjustments

Edit `/home/pi/inky-photo-frame/inky_photo_frame.py` (lines 40-43):

```python
# Color calibration settings for e-ink display
SATURATION = 0.5         # 0.0 = B&W, 1.0 = full color
AUTO_CONTRAST = True     # Enable/disable contrast enhancement
CONTRAST_CUTOFF = 1      # 0-5, lower = less aggressive
COLOR_TEMPERATURE = 0    # -50 to +50, negative = cooler/less yellow
```

## 🔧 Adjustment Guide

### If colors are still too yellow/green:

**Option 1: Reduce saturation**
```python
SATURATION = 0.4  # Try 0.3, 0.4, or 0.5
```

**Option 2: Disable auto-contrast**
```python
AUTO_CONTRAST = False  # Preserves original colors exactly
```

**Option 3: Cool down temperature** (experimental)
```python
COLOR_TEMPERATURE = -20  # Try values from -10 to -30
```

### If colors are too washed out:

```python
SATURATION = 0.7  # Increase saturation
CONTRAST_CUTOFF = 2  # More aggressive contrast
```

### If colors are perfect but contrast is low:

```python
CONTRAST_CUTOFF = 2  # Increase contrast without changing colors much
```

## 📊 Recommended Settings by Use Case

### For iPhone/Modern Phone Photos (Default)
```python
SATURATION = 0.5
AUTO_CONTRAST = True
CONTRAST_CUTOFF = 1
COLOR_TEMPERATURE = 0
```

### For DSLR/Professional Photos
```python
SATURATION = 0.6
AUTO_CONTRAST = False  # Photos already well-balanced
CONTRAST_CUTOFF = 0
COLOR_TEMPERATURE = 0
```

### For Old/Faded Photos
```python
SATURATION = 0.7
AUTO_CONTRAST = True
CONTRAST_CUTOFF = 3  # More aggressive to bring out details
COLOR_TEMPERATURE = 0
```

### For Black & White Mode
```python
SATURATION = 0.0  # Pure B&W
AUTO_CONTRAST = True
CONTRAST_CUTOFF = 2
COLOR_TEMPERATURE = 0
```

## 🧪 Testing Your Settings

```bash
# 1. Edit settings
nano ~/inky-photo-frame/inky_photo_frame.py

# 2. Restart service
sudo systemctl restart inky-photo-frame

# 3. Upload a test photo or wait for next rotation

# 4. Check logs to see applied settings
sudo journalctl -u inky-photo-frame -n 20 | grep -E "saturation|temperature|Converted"
```

## 🔍 Understanding the Changes

### P3 → sRGB Conversion
**What it does**: Converts iPhone's Display P3 color space to standard sRGB
**Why it helps**: E-ink displays expect sRGB, not P3
**Log message**: `Converted color profile to sRGB`

### Saturation
**What it does**: Controls color intensity
**0.0** = Black & white
**0.5** = Balanced (recommended)
**1.0** = Maximum color (may appear oversaturated)

### Auto-Contrast
**What it does**: Stretches histogram to use full brightness range
**Benefit**: Makes images pop more on e-ink
**Drawback**: Can shift colors slightly

### Contrast Cutoff
**What it does**: Ignores extreme pixels when calculating contrast
**Lower (0-1)**: Gentler, preserves original colors
**Higher (2-5)**: More aggressive, can shift colors

### Color Temperature
**What it does**: Shifts blue channel to compensate for yellow tint
**Negative (-20)**: Cooler, adds blue (reduces yellow/green)
**Positive (+20)**: Warmer, adds yellow
**Note**: Requires numpy, experimental feature

## 📸 Before/After Example

With v2.0.1 improvements:
- ✅ iPhone photos: Colors match original better
- ✅ Skin tones: More natural, less yellow
- ✅ Blues/greens: Accurate instead of shifted
- ✅ Overall: Balanced and pleasant

## ⚠️ Limitations

E-ink displays have limited color palettes:
- **Inky 7.3" (old)**: 7 colors (B/W/R/Y/O/G/B)
- **Inky 7.3" 2025**: 6 colors
- **Inky 13.3" 2025**: 6 colors

Some color shifts are **inherent to e-ink technology** and cannot be fully corrected. The improvements in v2.0.1 minimize these issues.

## 🆘 Still Having Issues?

If colors are still wrong after trying these settings:
1. Check your specific Inky model's color palette
2. Try a different test photo (some colors are outside e-ink gamut)
3. Verify logs: `sudo journalctl -u inky-photo-frame -f`
4. Report issue with example photo

---

**Updated for v2.0.1** - Color calibration improvements
