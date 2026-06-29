"""Phase 2 — Promptfoo export validity."""

import yaml

from qa_architect.export.promptfoo import to_promptfoo_config, to_promptfoo_yaml


def test_yaml_parses_and_matches_test_count(blueprint):
    text = to_promptfoo_yaml(blueprint)
    config = yaml.safe_load(text)
    assert "providers" in config
    assert config["prompts"] == ["{{input}}"]
    assert len(config["tests"]) == len(blueprint.tests)


def test_every_test_has_assert_and_input(blueprint):
    config = to_promptfoo_config(blueprint)
    for entry in config["tests"]:
        assert entry["vars"]["input"]
        assert entry["assert"]
        assert entry["assert"][0]["type"] in {
            "llm-rubric",
            "regex",
            "equals",
            "contains",
        }
        assert entry["metadata"]["requirement_ids"]
