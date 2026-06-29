---
title: Custom Python hooks
summary: Safe deterministic examples loaded from site_hooks.py.
docs_links: python::demo_links
hook_values:
  status: python::demo_status
  build_label: python::demo_build_label
  first_link: "{{ docs_links[0].label }}"
---

## Python module loading

`colophon.yml` declares `site_hooks.py` under `python.modules`. During build, Colophon imports that trusted local module and reads its `YAML_FUNCTIONS` registry.

## YAML usage

```yaml
signal_line:
  BUILD: python::demo_status
  HOOK: python::demo_build_label
```

Function results are copied before they are merged into page data. Duplicate names and missing functions fail with a path-aware error.
