# EDA Agent VSCode Extension — Publishing Guide

## Prerequisites

### 1. Node.js >= 18
```bash
node --version  # v20.x recommended
```

### 2. VSCE (Visual Studio Code Extension Manager)
```bash
npm install -g @vscode/vsce
```

### 3. Publisher Account
- Create a publisher at [https://marketplace.visualstudio.com/manage](https://marketplace.visualstudio.com/manage)
- Get your Personal Access Token (PAT) with `Marketplace > Publish` scope
- Login locally:
```bash
vsce login <publisher-name>
# Enter your PAT when prompted
```

## Local Development & Testing

### Install Dependencies
```bash
cd vscode-extension
npm install
```

### Compile
```bash
npm run compile
```

### Run in Extension Development Host
```bash
# In VSCode, open vscode-extension/ folder
# Press F5 or Run → Start Debugging
```

### Lint & Type Check
```bash
npm run lint
npm run check-types
```

## Packaging

### Build VSIX (Local Install)
```bash
npm run package
# This compiles TypeScript and copies media assets

npx vsce package --no-dependencies
# Creates: eda-agent-0.1.0.vsix
```

### Install VSIX Locally
```bash
# In VSCode
# Extensions → ... → Install from VSIX → Select .vsix file

# Or via CLI
code --install-extension eda-agent-0.1.0.vsix
```

## Version Bump & Release

### 1. Update Version
```bash
# Update package.json version field manually or:
npm version patch   # 0.1.0 → 0.1.1
npm version minor   # 0.1.0 → 0.2.0
npm version major   # 0.1.0 → 1.0.0
```

### 2. Update CHANGELOG.md
```markdown
## [0.1.1] - 2024-XX-XX
### Added
- New feature X
### Fixed
- Bug Y
```

### 3. Tag & Push
```bash
git add vscode-extension/package.json vscode-extension/CHANGELOG.md
git commit -m "chore: bump vscode-extension to v0.1.1"
git tag vscode-ext-v0.1.1
git push origin main --tags
```

### 4. Publish to Marketplace
```bash
cd vscode-extension
npm run compile
npx vsce publish --no-dependencies
```

Or publish a pre-release:
```bash
npx vsce publish --pre-release --no-dependencies
```

## Automated Release (GitHub Actions)

The repository includes two workflows:

### CI (`ci.yml`)
Triggers on push to `main`/`develop`:
- Lints TypeScript
- Type-checks
- Compiles
- Packages VSIX
- Uploads artifact

### Release (`release.yml`)
Triggers on tag push (`v*`):
- Builds and packages
- Creates GitHub Release with VSIX attached
- Publishes to VSCode Marketplace (requires `VSCE_PAT` secret)

### Setup Automated Publishing
1. Go to repository Settings → Secrets and variables → Actions
2. Add `VSCE_PAT` with your Visual Studio Marketplace PAT
3. Push a tag: `git tag v0.1.0 && git push origin v0.1.0`
4. GitHub Actions will automatically build, release, and publish

## Troubleshooting

### "Module not found" errors
```bash
rm -rf node_modules package-lock.json
npm install
```

### "Cannot find module 'vscode'"
```bash
npm install
# @types/vscode provides the vscode module types
```

### Icon not showing in marketplace
- Ensure `media/icon.png` exists (256x256 PNG recommended)
- Verify path in `package.json` icon field

### Extension fails to activate
- Check `out/extension.js` exists after `npm run compile`
- Verify `main` field in `package.json` points to correct file
- Check VSCode Developer Tools console for errors

## File Size Optimization

Before publishing, ensure the VSIX is reasonably sized:
```bash
ls -lh *.vsix
# Should be < 5MB for a lightweight extension
```

Excluded by `.vscodeignore`:
- Source TypeScript files
- Tests
- node_modules
- Development configs
- Git history
