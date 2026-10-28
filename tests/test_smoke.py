import importlib

MODULES = [
    "payequity", "payequity.cli", "payequity.ids", "payequity.config",
    "payequity.generators.master", "payequity.analytics.metrics",
    "payequity.workflow.approvals", "payequity.validation.checks", "payequity.export.manifest",
]


def test_package_modules_import():
    for name in MODULES:
        importlib.import_module(name)
