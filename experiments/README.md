# Experiments Directory

Experiment run directories are local artifacts and are ignored by git.

Use the naming pattern:

```text
{expid}_{YYYYMMDD}_{short_git_hash}/
```

Each run directory must include:

- config snapshot
- git commit hash
- environment lock file
- stdout/stderr logs
- metrics CSV
- key visualizations
