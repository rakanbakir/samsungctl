#!/bin/bash
# Uninstall script for SamsungCtl Arch Linux package

echo "Uninstalling SamsungCtl..."

# Check if package is installed
if ! pacman -Q samsungctl >/dev/null 2>&1; then
    echo "SamsungCtl is not installed."
    exit 1
fi

# Uninstall the package
sudo pacman -R samsungctl

echo "SamsungCtl has been uninstalled successfully!"