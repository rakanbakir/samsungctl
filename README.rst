=======================
This project has been updated
=======================

**Recent updates have added support for modern Samsung TVs with persistent pairing and automatic token management. The repository remains available for continued development.**

The most prominent fork as of the archival seems to be:
https://github.com/kdschlosser/samsungctl

----

==========
samsungctl
==========

samsungctl is a library and a command line tool for remote controlling Samsung
televisions via a TCP/IP connection. It currently supports both pre-2016 TVs as
well most of the modern Tizen-OS TVs with Ethernet or Wi-Fi connectivity.

Dependencies
============

- Python 3
- ``websocket-client`` (required for websocket method on 2016+ TVs)
- ``curses`` (optional, for the interactive mode)

Installation
============

samsungctl can be installed using `pip <(https://pip.pypa.io/>`_:

::

    # pip install samsungctl[websocket]

Alternatively you can clone the Git repository and run:

::

    # python setup.py install

For websocket support, install websocket-client:

::

    # pip install websocket-client

Arch Linux Package
==================

For Arch Linux users, you can install samsungctl as a native package:

::

    # Clone the repository
    git clone https://github.com/Ape/samsungctl.git
    cd samsungctl

    # Build and install the package
    ./build-pkg.sh
    sudo pacman -U samsungctl-0.7.1-1-any.pkg.tar.zst

    # Or uninstall later
    ./uninstall-pkg.sh

The package includes:
- System-wide installation to ``/usr/bin/samsungctl``
- Configuration file at ``/etc/samsungctl.conf``
- GUI remote application at ``/usr/share/samsungctl/samsungctl_remote_gui.py``
- Desktop menu entries for both CLI and GUI versions
- Icon and documentation

It's possible to use the command line tool without installation:

::

    $ python -m samsungctl

There is also a modern GUI remote control application with an eye-catching design:

::

    $ python samsungctl_remote_gui.py

The GUI can run without a configuration file and will show connection status. Use the IP configuration field at the bottom to set your TV's IP address.

The modern GUI features:
- Sleek dark theme with Samsung blue accent colors
- Professional header with Samsung logo and connection status indicator
- Intuitive remote control layout with power, volume/channel, navigation, and media controls
- Number pad for direct channel input
- Color-coded function buttons (A, B, C, D)
- Hover effects and modern button styling
- Real-time IP address configuration
- Persistent TV connection for instant response
- **Scrollable interface** with vertical and horizontal scrollbars for easy navigation
- **Keyboard scrolling support** (arrow keys, Page Up/Down, mouse wheel)
- **Improved mouse scrolling** with smoother 3x speed and Shift+wheel for horizontal scrolling
- **Scroll-to-top indicator** - click the ▲ button in top-right when scrolled down
- **Back button** added to function controls (sends KEY_RETURN)
- **Resizable window** that adapts to different screen sizes
- **App shortcuts** for popular streaming services (YouTube, Netflix, Prime Video, Disney+, HBO Max, Hulu)
  *App buttons open Smart Hub - navigate to your desired app using arrow keys and OK button*

**Keyboard Shortcuts:**
- **P** - Power toggle
- **M** - Mute
- **Space** - Play/Pause
- **=/-** - Volume up/down
- **C/V** - Channel up/down
- **Arrow Keys** - Navigation
- **Enter** - OK/Select
- **Escape** - Return/Back
- **0-9** - Direct channel numbers

**Mouse Controls:**
- **Mouse Wheel** - Vertical scrolling (3x speed)
- **Shift + Mouse Wheel** - Horizontal scrolling

Command line usage
==================

You can use ``samsungctl`` command to send keys to a TV:

::

    $ samsungctl --host <host> [options] <key> [key ...]

``host`` is the hostname or IP address of the TV. ``key`` is a key code, e.g.
``KEY_VOLDOWN``. See `Key codes`_.

There is also an interactive mode (ncurses) for sending the key presses:

::

    $ samsungctl --host <host> [options] --interactive

Use ``samsungctl --help`` for more information about the command line
arguments:

::

    usage: samsungctl [-h] [--version] [-v] [-q] [-i] [--host HOST] [--port PORT]
                      [--method METHOD] [--name NAME] [--description DESC]
                      [--id ID] [--timeout TIMEOUT]
                      [key [key ...]]

    Remote control Samsung televisions via TCP/IP connection

    positional arguments:
      key                 keys to be sent (e.g. KEY_VOLDOWN)

    optional arguments:
      -h, --help          show this help message and exit
      --version           show program's version number and exit
      -v, --verbose       increase output verbosity
      -q, --quiet         suppress non-fatal output
      -i, --interactive   interactive control
      --host HOST         TV hostname or IP address
      --port PORT         TV port number (TCP)
      --method METHOD     Connection method (legacy or websocket)
      --name NAME         remote control name
      --description DESC  remote control description
      --id ID             remote control id
      --timeout TIMEOUT   socket timeout in seconds (0 = no timeout)

    E.g. samsungctl --host 192.168.0.10 --name myremote KEY_VOLDOWN

The settings can be loaded from a configuration file. The file is searched from
``$XDG_CONFIG_HOME/samsungctl.conf``, ``~/.config/samsungctl.conf``, and
``/etc/samsungctl.conf`` in this order. A simple default configuration is
bundled with the source as `samsungctl.conf <samsungctl.conf>`_.

**Persistent Pairing**: For websocket connections to modern TVs, the tool automatically
retrieves and saves an authentication token after the first authorization. Subsequent
runs use the saved token for direct connection without re-authorization. The config
is saved to ``~/.config/samsungctl.conf`` after successful connection.

Library usage
=============

samsungctl can be imported as a Python 3 library:

.. code-block:: python

    import samsungctl

A context managed remote controller object of class ``Remote`` can be
constructed using the ``with`` statement:

.. code-block:: python

    with samsungctl.Remote(config) as remote:
        # Use the remote object

The constructor takes a configuration dictionary as a parameter. All
configuration items must be specified.

===========  ======  ===========================================
Key          Type    Description
===========  ======  ===========================================
host         string  Hostname or IP address of the TV.
port         int     TCP port number. (Default: ``55000``)
method       string  Connection method (``legacy`` or ``websocket``)
name         string  Name of the remote controller.
description  string  Remote controller description.
id           string  Additional remote controller ID.
timeout      int     Timeout in seconds. ``0`` means no timeout.
token        string  Authentication token (auto-retrieved for websocket).
paired       bool    Pairing status (auto-set for websocket).
===========  ======  ===========================================

The ``Remote`` object is very simple and you only need the ``control(key)``
method. The only parameter is a string naming the key to be sent (e.g.
``KEY_VOLDOWN``). See `Key codes`_. You can call ``control`` multiple times
using the same ``Remote`` object. The connection is automatically closed when
exiting the ``with`` statement.

When something goes wrong you will receive an exception:

=================  =======================================
Exception          Description
=================  =======================================
AccessDenied       The TV does not allow you to send keys.
ConnectionClosed   The connection was closed.
UnhandledResponse  An unexpected response was received.
socket.timeout     The connection timed out.
=================  =======================================

Example program
---------------

This simple program opens and closes the menu a few times.

.. code-block:: python

    #!/usr/bin/env python3

    import samsungctl
    import time

    config = {
        "name": "samsungctl",
        "description": "PC",
        "id": "",
        "host": "192.168.0.10",
        "port": 55000,
        "method": "legacy",
        "timeout": 0,
    }

    with samsungctl.Remote(config) as remote:
        for i in range(10):
            remote.control("KEY_MENU")
            time.sleep(0.5)

For modern TVs, use websocket method with automatic SSL fallback:

.. code-block:: python

    config = {
        "name": "samsungctl",
        "host": "192.168.0.10",
        "method": "websocket",
        "timeout": 0,
    }

    with samsungctl.Remote(config) as remote:
        remote.control("KEY_VOLUP")  # First run prompts for auth, saves token

Key codes
=========

The list of accepted keys may vary depending on the TV model, but the following
list has some common key codes and their descriptions.

=================  ============
Key code           Description
=================  ============
KEY_POWEROFF       Power off
KEY_UP             Up
KEY_DOWN           Down
KEY_LEFT           Left
KEY_RIGHT          Right
KEY_CHUP           P Up
KEY_CHDOWN         P Down
KEY_ENTER          Enter
KEY_RETURN         Return
KEY_CH_LIST        Channel List
KEY_MENU           Menu
KEY_SOURCE         Source
KEY_GUIDE          Guide
KEY_TOOLS          Tools
KEY_INFO           Info
KEY_RED            A / Red
KEY_GREEN          B / Green
KEY_YELLOW         C / Yellow
KEY_BLUE           D / Blue
KEY_PANNEL_CHDOWN  3D
KEY_VOLUP          Volume Up
KEY_VOLDOWN        Volume Down
KEY_MUTE           Mute
KEY_0              0
KEY_1              1
KEY_2              2
KEY_3              3
KEY_4              4
KEY_5              5
KEY_6              6
KEY_7              7
KEY_8              8
KEY_9              9
KEY_DTV            TV Source
KEY_HDMI           HDMI Source
KEY_CONTENTS       SmartHub
=================  ============

Please note that some codes are different on the 2016+ TVs. For example,
``KEY_POWEROFF`` is ``KEY_POWER`` on the newer TVs. Use the ``websocket`` method
for modern TVs, which automatically handles SSL connections and token authentication.

References
==========

I did not reverse engineer the control protocol myself and samsungctl is not
the only implementation. Here is the list of things that inspired samsungctl.

- http://sc0ty.pl/2012/02/samsung-tv-network-remote-control-protocol/
- https://gist.github.com/danielfaust/998441
- https://github.com/Bntdumas/SamsungIPRemote
- https://github.com/kyleaa/homebridge-samsungtv2016
- https://github.com/kdschlosser/samsungctl (fork with additional features)
