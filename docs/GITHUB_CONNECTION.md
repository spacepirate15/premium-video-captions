# Reliable GitHub Connection for Local Agent Workspaces

The reliable setup is machine-level GitHub CLI authentication plus normal Git remotes. Do not solve this separately per workspace.

## Recommended Setup

Install GitHub CLI once:

```bash
brew install gh
```

Authenticate once:

```bash
gh auth login --hostname github.com --git-protocol https --scopes repo,workflow
```

Then configure Git to reuse that authenticated GitHub session:

```bash
gh auth setup-git
```

Verify from any workspace:

```bash
gh auth status
git config --global credential.helper
```

## Why This Is the Better Default

Codex can use a GitHub connector when that connector is enabled for a session, but local repository work still needs local credentials for `git push`, `git fetch`, branch operations, release workflows, and GitHub Actions inspection through `gh`.

Using `gh auth setup-git` stores credentials in the operating system credential store and makes GitHub access available from any repository on the machine. The workspace only needs a normal remote:

```bash
git remote add origin https://github.com/<owner>/<repo>.git
```

This avoids per-project tokens, pasted credentials, and brittle environment variables.

## SSH Alternative

SSH remotes are also reliable for Git-only operations:

```bash
ssh-keygen -t ed25519 -C "you@example.com"
```

Then add the public key to GitHub and use:

```bash
git remote add origin git@github.com:<owner>/<repo>.git
```

SSH is good for pushing and pulling. GitHub CLI is still better for agents because it also covers repository creation, pull requests, issue work, and Actions logs.
