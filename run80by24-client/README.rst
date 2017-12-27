=============
80by24 client
=============

This command-line application turns your terminal into a screen which you can
control through the `80by24 service <https://80by24.net>`_.

----------
Installing
----------

`Install using pip <https://packaging.python.org/tutorials/installing-packages/>`_ on a system with Python>=3.5::

  pip install 80by24-client

-------
Running
-------

::

  80by24

will run the client. `Ctrl-C` aborts.

-------------
Configuration
-------------

Out of the box, the client generates a random passphrase and connects to `80by24.net`. This can be changed by
putting a configuration file into `~/.80by24.conf` of the following form::

  host:       http://localhost:8080
  passphrase: correct horse battery staple

