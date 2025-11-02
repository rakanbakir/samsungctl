#!/bin/bash
# Build script for testing the Arch Linux package locally

set -e

echo "Building SamsungCtl Arch Linux package..."

# Create source tarball
echo "Creating source tarball..."
PROJECT_DIR="$(pwd)"
cd ..
mkdir -p /tmp/samsungctl-build
cp -r "$PROJECT_DIR"/* /tmp/samsungctl-build/ 2>/dev/null || true
cd /tmp/samsungctl-build
find . -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "venv" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "pkg" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pkg.tar.zst" -delete 2>/dev/null || true
cd ..
tar -czf "$PROJECT_DIR/samsungctl-0.7.1.tar.gz" samsungctl-build
rm -rf /tmp/samsungctl-build

# Move back to package directory
cd "$PROJECT_DIR"

# Build the package
echo "Building package..."
makepkg -f

echo "Package built successfully!"
echo "You can install it with: sudo pacman -U samsungctl-0.7.1-1-any.pkg.tar.zst"
echo "Or test it first: pacman -Qip samsungctl-0.7.1-1-any.pkg.tar.zst"