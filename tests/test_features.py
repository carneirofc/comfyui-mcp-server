"""Tests for the feature-flag parser and opt-in tool registration."""

import pytest

from feature_flags import KNOWN_FEATURES, parse_features
from tools.models import register_model_tools
from tools.nodes import register_node_tools
from tools.system import register_system_tools
from tools.jobs_api import register_jobs_api_tools
from tools.upload import register_upload_tools


class TestParseFeatures:
    def test_none_default(self):
        assert parse_features(None) == (set(), [])
        assert parse_features("") == (set(), [])
        assert parse_features("none") == (set(), [])

    def test_all_token(self):
        enabled, unknown = parse_features("all")
        assert enabled == set(KNOWN_FEATURES)
        assert unknown == []

    def test_comma_and_space_separated(self):
        enabled, unknown = parse_features("models, system")
        assert enabled == {"models", "system"}
        assert unknown == []
        enabled2, _ = parse_features("models system")
        assert enabled2 == {"models", "system"}

    def test_case_insensitive(self):
        enabled, _ = parse_features("Models,SYSTEM")
        assert enabled == {"models", "system"}

    def test_unknown_reported(self):
        enabled, unknown = parse_features("models,bogus,nope")
        assert enabled == {"models"}
        assert unknown == ["bogus", "nope"]

    def test_all_overrides_others(self):
        enabled, unknown = parse_features("models,all,bogus")
        assert enabled == set(KNOWN_FEATURES)
        assert unknown == []


class FakeMCP:
    """Records tool registrations the way FastMCP.tool() is used."""

    def __init__(self):
        self.tools = []

    def tool(self):
        def decorator(fn):
            self.tools.append(fn.__name__)
            return fn
        return decorator


class FakeClient:
    def get_models(self, folder=None):
        if folder is None:
            return ["checkpoints", "loras", "embeddings"]
        return [f"{folder}_a.safetensors", f"{folder}_b.safetensors"]

    def get_object_info(self, class_type=None):
        return {
            "KSampler": {
                "input": {"required": {
                    "sampler_name": [["euler", "dpmpp_2m"]],
                    "scheduler": [["normal", "karras"]],
                }}
            }
        }

    def get_system_stats(self):
        return {"system": {}, "devices": []}

    def get_features(self):
        return {"assets": False}

    def get_jobs(self, limit=20, status=None):
        return {"jobs": [{"id": "j1"}]}


class TestRegistrationGating:
    def test_each_group_registers_expected_tools(self):
        cases = [
            (register_model_tools, {"list_model_folders", "list_models_in_folder", "list_embeddings"}),
            (register_node_tools, {"get_node_info", "list_samplers", "list_schedulers"}),
            (register_system_tools, {"get_system_stats", "get_capabilities", "interrupt_job", "free_memory"}),
            (register_jobs_api_tools, {"list_jobs", "get_job_detail"}),
            (register_upload_tools, {"upload_image", "upload_mask"}),
        ]
        for register, expected in cases:
            mcp = FakeMCP()
            register(mcp, FakeClient())
            assert set(mcp.tools) == expected

    def test_model_tools_call_through(self):
        mcp = FakeMCP()
        registered = {}

        # Capture the actual functions to invoke them.
        def tool():
            def deco(fn):
                registered[fn.__name__] = fn
                return fn
            return deco

        mcp.tool = tool
        register_model_tools(mcp, FakeClient())

        assert registered["list_model_folders"]()["folders"] == ["checkpoints", "loras", "embeddings"]
        assert registered["list_models_in_folder"]("loras")["count"] == 2
        assert registered["list_embeddings"]()["embeddings"] == ["embeddings_a.safetensors", "embeddings_b.safetensors"]

    def test_node_tools_extract_enums(self):
        registered = {}
        mcp = FakeMCP()

        def tool():
            def deco(fn):
                registered[fn.__name__] = fn
                return fn
            return deco

        mcp.tool = tool
        register_node_tools(mcp, FakeClient())

        assert registered["list_samplers"]()["samplers"] == ["euler", "dpmpp_2m"]
        assert registered["list_schedulers"]()["schedulers"] == ["normal", "karras"]
