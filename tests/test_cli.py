import pytest
from newsletter_archive import cli

def test_subcommands_registered():
    parser = cli.build_parser()
    for sub in ["ingest", "build", "backfill", "migrate"]:
        ns = parser.parse_args([sub])
        assert ns.command == sub

def test_brand_subcommand_has_actions():
    parser = cli.build_parser()
    ns = parser.parse_args(["brand", "set-category", "sephora.com", "beauty"])
    assert ns.command == "brand" and ns.action == "set-category"
    assert ns.key == "sephora.com" and ns.value == "beauty"

def test_unknown_command_exits():
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["frobnicate"])
