# Maintainer: Rakan Bakir <rakanbakir@github.com>
pkgname=samsungctl
pkgver=0.8.0
pkgrel=1
pkgdesc="Remote control Samsung televisions via TCP/IP connection"
arch=('any')
url="https://github.com/rakanbakir/samsungctl"
license=('MIT')
depends=('python' 'python-websocket-client' 'python-pillow')
makedepends=('python-setuptools')
optdepends=('python-curses: for interactive UI')
source=("$pkgname-$pkgver.tar.gz::https://github.com/rakanbakir/samsungctl/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$srcdir/samsungctl-build"
    python setup.py build
}

package() {
    cd "$srcdir/samsungctl-build"

    # Install Python package
    python setup.py install --root="$pkgdir" --optimize=1 --skip-build

    # Install license
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"

    # Install documentation
    install -Dm644 README.rst "$pkgdir/usr/share/doc/$pkgname/README.rst"

    # Install configuration file
    install -Dm644 samsungctl.conf "$pkgdir/etc/samsungctl.conf"

    # Install icon
    install -Dm644 samsung_icon.png "$pkgdir/usr/share/icons/hicolor/128x128/apps/samsungctl.png"

    # Install GUI remote script
    install -Dm755 samsungctl_remote_gui.py "$pkgdir/usr/share/samsungctl/samsungctl_remote_gui.py"

    # Create desktop file for CLI
    install -Dm644 /dev/stdin "$pkgdir/usr/share/applications/samsungctl.desktop" <<EOF
[Desktop Entry]
Name=Samsung TV Remote (CLI)
Comment=Command-line remote control for Samsung televisions
Exec=konsole -e samsungctl --interactive
Icon=samsungctl
Terminal=false
Type=Application
Categories=Utility;AudioVideo;
EOF

    # Create desktop file for GUI
    install -Dm644 /dev/stdin "$pkgdir/usr/share/applications/samsungctl-gui.desktop" <<EOF
[Desktop Entry]
Name=Samsung TV Remote (GUI)
Comment=GUI remote control for Samsung televisions
Exec=python /usr/share/samsungctl/samsungctl_remote_gui.py
Icon=samsungctl
Terminal=false
Type=Application
Categories=Utility;AudioVideo;
EOF
}