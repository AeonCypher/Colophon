---
title: Deploy dry-run
summary: The scaffold includes content/deploy.example.yaml so deploy config can be resolved without uploading.
deploy_checks:
  - Set EXAMPLE_FTP_PASSWORD before running deploy because the example uses env::EXAMPLE_FTP_PASSWORD.
  - Use --dry-run to print planned actions without posting, uploading, or deleting remote files.
  - The scaffold deploy steps are preflight_build, build, and upload.
  - Real sites can add mastodon_post and enable_comments when their Mastodon config is ready.
---

## Dry-run command

```bash
EXAMPLE_FTP_PASSWORD=dummy colophon deploy --config colophon.yml --dry-run
```

## Example target

The scaffold target uses `ftps`, `example.test`, and `public_html/example.test/`. Replace those values before a real deploy.
