import asyncio
import unittest

import src.server as server


def _accepts_null(schema):
    if "anyOf" in schema:
        return any(_accepts_null(s) for s in schema["anyOf"])
    t = schema.get("type")
    return t is None or t == "null" or (isinstance(t, list) and "null" in t)


class TestToolSchemas(unittest.TestCase):
    """A parameter advertised with "default": null must also accept null."""

    def test_null_defaults_accept_null(self):
        tools = asyncio.run(server.mcp.list_tools())
        bad = [
            f"{tool.name}.{name}"
            for tool in tools
            for name, prop in tool.inputSchema.get("properties", {}).items()
            if "default" in prop and prop["default"] is None and not _accepts_null(prop)
        ]
        self.assertEqual(bad, [], f"default null but null rejected: {bad}")

    def test_eldo_layout_accepts_null_and_json_text(self):
        meta = server.mcp._tool_manager.get_tool("eldo").fn_metadata
        meta.arg_model.model_validate({"action": "visualize_waveforms", "layout": None})
        parsed = meta.pre_parse_json({"layout": '[{"signals": ["v(out)"]}]'})
        args = meta.arg_model.model_validate(parsed)
        self.assertEqual(args.layout, [{"signals": ["v(out)"]}])


if __name__ == "__main__":
    unittest.main()
