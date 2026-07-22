import os
from typing import Any, Dict, Mapping, Optional


def apply_runtime_hw_overrides(
    profile: Optional[Dict[str, Any]],
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    """Applies runtime hardware overrides exported by the launcher process."""
    effective_profile: Dict[str, Any] = dict(profile or {})
    runtime_env = env or os.environ

    fake_vendor = runtime_env.get("SHADOWGRAM_FAKE_VENDOR", "").strip()
    fake_model = runtime_env.get("SHADOWGRAM_FAKE_MODEL", "").strip()
    device_name = runtime_env.get("SHADOWGRAM_DEVICE_NAME", "").strip()

    if fake_model:
        if fake_vendor and not fake_model.lower().startswith(fake_vendor.lower()):
            effective_profile["device_model"] = f"{fake_vendor} {fake_model}"
        else:
            effective_profile["device_model"] = fake_model
    elif device_name and not effective_profile.get("device_model"):
        effective_profile["device_model"] = device_name

    if device_name:
        effective_profile["runtime_device_name"] = device_name
    if fake_vendor:
        effective_profile["runtime_fake_vendor"] = fake_vendor
    if fake_model:
        effective_profile["runtime_fake_model"] = fake_model

    return effective_profile
