# CameraBlur Test Suite

Comprehensive testing suite for the CameraBlur project, achieving high code coverage across all critical modules.

## Test Structure

The test suite is organized by module:

- `test_exceptions.py` - Tests for custom exception hierarchy
- `test_config.py` - Tests for configuration models and validation  
- `test_performance.py` - Tests for FPS counter and performance monitoring
- `test_system_check.py` - Tests for system requirements checking (v4l2loopback, cameras)
- `test_background_loader.py` - Tests for background image/video loading
- `test_video_loop.py` - Tests for threaded video background loop
- `test_pipeline_capture.py` - Tests for camera capture module
- `test_pipeline_effects.py` - Tests for effects processor (blur, replacement)
- `test_pipeline_output.py` - Tests for virtual camera output
- `test_pipeline_segmentation.py` - Tests for MediaPipe segmentation
- `test_pipeline_rvm.py` - Tests for RVM GPU-accelerated segmentation
- `test_pipeline_init.py` - Tests for pipeline orchestrator
- `test_cli.py` - Tests for CLI commands and argument parsing
- `test_integration.py` - Integration tests for end-to-end workflows
- `conftest.py` - Shared fixtures and test configuration

## Running Tests

### Run all tests with coverage:
```bash
pytest --cov=src/camerablur --cov-report=html --cov-report=term
```

### Run specific test file:
```bash
pytest tests/test_config.py -v
```

### Run tests by marker:
```bash
pytest -m "not slow"  # Skip slow tests
pytest -m integration  # Only integration tests
```

### Generate coverage report:
```bash
pytest --cov=src/camerablur --cov-report=html
# Open htmlcov/index.html in browser
```

## Coverage Goals

Target: 90%+ coverage for core modules

Modules intentionally excluded from coverage requirements:
- TUI modules (interactive UI, difficult to test automatically)
- __main__.py (entry point, minimal logic)

## Test Fixtures

Common fixtures defined in `conftest.py`:
- `sample_frame` - 640x480 BGR frame for testing
- `sample_mask` - Segmentation mask with person silhouette
- `sample_image` - Random test image
- `mock_*_config` - Mock configuration objects for all config types
- `mock_app_config` - Complete mock application configuration

## Writing Tests

### Best Practices:
1. Use descriptive test names that explain what is being tested
2. Follow AAA pattern: Arrange, Act, Assert
3. Mock external dependencies (OpenCV, PyTorch, camera devices)
4. Test both success and failure cases
5. Use parametrize for testing multiple similar cases
6. Keep tests independent and isolated

### Example Test:
```python
def test_blur_effect_with_custom_intensity(mock_effect_config, sample_frame, sample_mask):
    """Test blur effect with custom intensity setting."""
    # Arrange
    mock_effect_config.mode = EffectMode.BLUR
    mock_effect_config.blur_intensity = 31
    processor = EffectsProcessor(mock_effect_config)
    
    # Act
    result = processor.process(sample_frame, sample_mask)
    
    # Assert
    assert result.shape == sample_frame.shape
    assert result.dtype == np.uint8
```

## Continuous Integration

The test suite is designed to run in CI environments:
- Fast execution (< 2 minutes for core tests)
- Mocked hardware dependencies
- No GPU required (PyTorch/CUDA mocked)
- No camera devices required (cv2.VideoCapture mocked)

## Troubleshooting

### Tests timing out:
- Some tests with threading may be slow
- Skip with: `pytest -m "not slow"`

### ImportError for modules:
- Install dev dependencies: `pip install -e ".[dev]"`
- Or with uv: `uv pip install -e ".[dev]"`

### Coverage not including source:
- Ensure running from project root
- Check `src/camerablur` is in Python path
