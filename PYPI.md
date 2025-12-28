# PyPI Publishing Setup

## Trusted Publisher Configuration

To publish to PyPI using GitHub Actions with OIDC (OpenID Connect), you must configure a Trusted Publisher on PyPI.

### Required Configuration

Go to https://pypi.org/manage/project/wood_nano/settings/publishing/ and add a new publisher with these **exact** values:

| Field | Value |
|-------|-------|
| Owner | `petrasvestartas` |
| Repository name | `wood_nano` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

> **Important**: The environment name must match exactly what is specified in the workflow file. If you already have a publisher configured without the environment name, you must **delete it** and create a new one with the environment name specified.

## Workflow Configuration

The `release.yml` workflow uses GitHub Environments for additional security. The relevant section:

```yaml
publish:
  needs: [build_sdist, build_wheels]
  runs-on: ubuntu-latest
  environment:
    name: pypi
    url: https://pypi.org/project/wood_nano
  permissions:
    id-token: write

  steps:
    - uses: actions/download-artifact@v4
      with:
        pattern: wheels-*
        path: dist
        merge-multiple: true

    - uses: actions/download-artifact@v4
      with:
        name: sdist
        path: dist

    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
```

## Troubleshooting

### Error: `invalid-publisher: valid token, but no corresponding publisher`

This error occurs when:
1. No Trusted Publisher is configured on PyPI
2. The Trusted Publisher is configured without the environment name
3. The repository owner, name, workflow filename, or environment name doesn't match exactly

**Solution**: Verify all fields match exactly between your workflow and PyPI configuration.

### Claims Debug Information

When the publish fails, PyPI provides the claims being sent. Verify these match your Trusted Publisher configuration:

- `repository`: `petrasvestartas/wood_nano`
- `repository_owner`: `petrasvestartas`
- `workflow_ref`: `petrasvestartas/wood_nano/.github/workflows/release.yml@refs/tags/v*`
- `environment`: `pypi`

## Additional Notes

### Why Use GitHub Environments?

Using `environment: pypi` in the workflow provides:
- Deployment protection rules
- Required reviewers before publishing
- Environment-specific secrets
- Audit trail of deployments

### Alternative: Publishing Without Environment

If you prefer not to use GitHub Environments, remove the `environment` block from the workflow and configure the Trusted Publisher on PyPI **without** an environment name.

## References

- [PyPI Trusted Publishers Documentation](https://docs.pypi.org/trusted-publishers/)
- [PyPI Trusted Publishers Troubleshooting](https://docs.pypi.org/trusted-publishers/troubleshooting/)
- [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
