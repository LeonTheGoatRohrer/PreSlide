"""PreSlide Pipeline B: Sentinel-2 before/after change signature of documented landslides.

This package intentionally uses POST-event imagery. It is an event-detection / label-QA system and is kept
strictly separate from the precursor model (Pipeline A, `preslide` and `preslide.v04`): nothing here is imported
by Pipeline A, and nothing here writes outside data/satellite, models/satellite and reports/satellite.
Detected changes are `satellite_detected_candidate` with validation_status UNVERIFIED until independently validated.
"""
