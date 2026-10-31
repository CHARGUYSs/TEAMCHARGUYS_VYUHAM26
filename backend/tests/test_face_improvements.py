"""Regression tests for robust enrollment and unknown-person fallbacks.
These are logic tests, not measured accuracy on real consented faces."""
import json
import numpy as np
import pytest

from app import face_identity


def vec(index):
    arr = np.zeros(128, dtype=np.float32)
    arr[index] = 1.
    return arr


def patch_pipeline(monkeypatch, detected):
    monkeypatch.setattr(face_identity, "_load_models", lambda: None)
    monkeypatch.setattr(face_identity, "_detector", object())
    monkeypatch.setattr(face_identity, "_recognizer", object())
    monkeypatch.setattr(face_identity, "_faces_with_features", lambda image: detected)


def image():
    return np.zeros((200, 200, 3), dtype=np.uint8)


def box(feature, **kwargs):
    return {
        "vector": feature,
        "box": {"x": 0.2, "y": 0.2, "width": 0.5, "height": 0.5},
        "quality": kwargs.get("quality", {"advice": []}),
    }


def test_quality_rejects_low_light_enrollment(monkeypatch):
    patch_pipeline(monkeypatch, [box(vec(0), quality={"advice": ["Move to brighter, even lighting."]})])
    with pytest.raises(ValueError, match="brighter"):
        face_identity.extract_enrollment(image())


def test_consent_templates_do_not_guess_unenrolled(monkeypatch):
    patch_pipeline(monkeypatch, [box(vec(7))])
    result = face_identity.recognize(image(), [(1, "Alex", "friend", json.dumps(vec(0).tolist()))])
    assert result[0]["status"] == "unknown"
    assert result[0]["name"] is None
    assert result[0]["reason"] == "low_similarity"


def test_ambiguous_face_with_identical_descriptors_stays_unknown(monkeypatch):
    patch_pipeline(monkeypatch, [box(vec(0))])
    templates = [
        (1, "Alex", "friend", json.dumps(vec(0).tolist())),
        (2, "Sam", "sibling", json.dumps(vec(0).tolist())),
    ]
    result = face_identity.recognize(image(), templates)[0]
    assert result["status"] == "unknown"
    assert result["reason"] == "ambiguous"
    assert result["name"] is None


def test_multi_sample_matching_with_clear_separation(monkeypatch):
    patch_pipeline(monkeypatch, [box(vec(0))])
    templates = [
        (1, "Alex", "friend", json.dumps(vec(0).tolist())),
        (1, "Alex", "friend", json.dumps(vec(0).tolist())),
        (2, "Sam", "sibling", json.dumps(vec(1).tolist())),
    ]
    result = face_identity.recognize(image(), templates)[0]
    assert result["status"] == "matched"
    assert result["name"] == "Alex"
    assert result["enrolled_samples"] == 2


def test_missing_model_status_is_actionable(monkeypatch):
    monkeypatch.setattr(face_identity, "_load_models", lambda: None)
    monkeypatch.setattr(face_identity, "_detector", None)
    monkeypatch.setattr(face_identity, "_recognizer", None)
    monkeypatch.setattr(face_identity, "_model_error", "models unavailable")
    state = face_identity.model_status()
    assert state["ready"] is False
    assert "models unavailable" in state["message"]


def test_same_photo_similarity_detectable():
    assert face_identity.cosine_similarity(vec(0).tolist(), json.dumps(vec(0).tolist())) > .997
    assert face_identity.cosine_similarity(vec(0).tolist(), json.dumps(vec(1).tolist())) < .1


def test_low_quality_frame_cannot_receive_person_name(monkeypatch):
    patch_pipeline(monkeypatch, [box(vec(0), quality={
        "advice": ["Hold the camera steady and focus on the face."],
        "sharpness": 3, "brightness": 100, "face_size_px": 110
    })])
    result = face_identity.recognize(image(), [
        (1, "Alex", "friend", json.dumps(vec(0).tolist()))
    ])[0]
    assert result["status"] == "unknown"
    assert result["reason"] == "low_quality"
    assert result["person_id"] is None


def test_multi_photo_requires_more_than_one_supporting_sample(monkeypatch):
    # One matching face plus one very different/mislabeled enrollment photo
    # must not be enough to announce a person's name.
    patch_pipeline(monkeypatch, [box(vec(0))])
    result = face_identity.recognize(image(), [
        (1, "Alex", "friend", json.dumps(vec(0).tolist())),
        (1, "Alex", "friend", json.dumps(vec(1).tolist())),
    ])[0]
    assert result["status"] == "unknown"
    assert result["reason"] == "inconsistent_samples"
    assert result["name"] is None
