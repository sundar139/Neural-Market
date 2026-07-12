# Environment Reports

Generated environment provenance reports are written here by:

```powershell
neuralmarket environment check --config configs/reproducibility/default.yaml --output reports/environment/environment_check.json
```

Generated `*.json` and `*.txt` files in this directory are ignored by Git. Only
this README is tracked. Reports capture Python, platform, dependency, Git, and
reproducibility metadata. They never contain environment-variable values,
credentials, or other secrets — only whether supported variables are configured.
