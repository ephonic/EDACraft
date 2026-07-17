#!/usr/bin/env node
/**
 * Manual VSIX packager for EDA Agent extension.
 * VSIX is just a ZIP file with a specific structure.
 * This script avoids dependency on vsce CLI which may have Node.js compatibility issues.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const EXT_DIR = path.resolve(__dirname, '..');
const PACKAGE_JSON = require(path.join(EXT_DIR, 'package.json'));
const VERSION = PACKAGE_JSON.version;
const NAME = PACKAGE_JSON.name;
const VSIX_NAME = `${NAME}-${VERSION}.vsix`;
const BUILD_DIR = path.join(EXT_DIR, 'build');
const STAGING_DIR = path.join(BUILD_DIR, 'extension');

function clean() {
    if (fs.existsSync(BUILD_DIR)) {
        fs.rmSync(BUILD_DIR, { recursive: true });
    }
    fs.mkdirSync(STAGING_DIR, { recursive: true });
}

function copyFiles() {
    const filesToCopy = [
        'package.json',
        'README.md',
        'CHANGELOG.md',
        'LICENSE',
    ];

    for (const file of filesToCopy) {
        const src = path.join(EXT_DIR, file);
        if (fs.existsSync(src)) {
            fs.copyFileSync(src, path.join(STAGING_DIR, file));
        }
    }

    // Copy out/ directory
    const outSrc = path.join(EXT_DIR, 'out');
    const outDst = path.join(STAGING_DIR, 'out');
    if (fs.existsSync(outSrc)) {
        copyDir(outSrc, outDst);
    } else {
        console.error('ERROR: out/ directory not found. Run "npm run compile" first.');
        process.exit(1);
    }

    // Copy media directory
    const mediaSrc = path.join(EXT_DIR, 'media');
    const mediaDst = path.join(STAGING_DIR, 'media');
    if (fs.existsSync(mediaSrc)) {
        copyDir(mediaSrc, mediaDst);
    }

    // Copy Python backend source (bundled, no pip install needed).
    // We place it under python/eda_agent/ so PYTHONPATH=extension/python
    // allows "import eda_agent" to resolve correctly.
    // Third-party deps (pydantic, openai, etc.) are NOT bundled here;
    // they are auto-installed on first launch via ensurePythonDependencies().
    const pySrc = path.join(EXT_DIR, '..', 'src', 'eda_agent');
    const pyDst = path.join(STAGING_DIR, 'python', 'eda_agent');
    if (fs.existsSync(pySrc)) {
        copyDir(pySrc, pyDst);
        console.log(`   Copied Python backend: ${pySrc} -> ${pyDst}`);
    } else {
        console.warn('   WARNING: Python backend source not found at ../src/eda_agent');
        console.warn('   Fallback: user must install eda-agent via pip');
    }
}

function copyDir(src, dst) {
    fs.mkdirSync(dst, { recursive: true });
    const entries = fs.readdirSync(src, { withFileTypes: true });
    for (const entry of entries) {
        const srcPath = path.join(src, entry.name);
        const dstPath = path.join(dst, entry.name);
        if (entry.isDirectory()) {
            // Skip Python cache and hidden dirs
            if (entry.name === '__pycache__' || entry.name === '.git' || entry.name === '.pytest_cache') {
                continue;
            }
            copyDir(srcPath, dstPath);
        } else {
            // Skip compiled Python and hidden files
            if (entry.name.endsWith('.pyc') || entry.name === '.DS_Store') {
                continue;
            }
            fs.copyFileSync(srcPath, dstPath);
        }
    }
}

function createVSIX() {
    const vsixPath = path.join(EXT_DIR, VSIX_NAME);
    
    // Remove old VSIX
    if (fs.existsSync(vsixPath)) {
        fs.unlinkSync(vsixPath);
    }

    // Use system zip command
    try {
        execSync(`cd "${BUILD_DIR}" && zip -r "${vsixPath}" extension`, {
            stdio: 'inherit'
        });
        console.log(`\n✅ Created: ${vsixPath}`);
        
        const stats = fs.statSync(vsixPath);
        console.log(`   Size: ${(stats.size / 1024).toFixed(1)} KB`);
    } catch (err) {
        console.error('ERROR: Failed to create VSIX. Make sure "zip" is installed.');
        console.error(err.message);
        process.exit(1);
    }
}

function validate() {
    const required = [
        path.join(STAGING_DIR, 'package.json'),
        path.join(STAGING_DIR, 'out', 'extension.js'),
    ];
    
    for (const file of required) {
        if (!fs.existsSync(file)) {
            console.error(`ERROR: Required file missing: ${path.relative(STAGING_DIR, file)}`);
            process.exit(1);
        }
    }
    
    console.log('✅ Validation passed');
}

function main() {
    console.log(`📦 Packaging ${NAME} v${VERSION}...\n`);
    
    clean();
    copyFiles();
    validate();
    createVSIX();
    
    console.log('\n🎉 Done! Install with:');
    console.log(`   code --install-extension ${VSIX_NAME}`);
}

main();
