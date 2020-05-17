# prologix3.py
This package contains the Python 3 module prologix3.py, written to talk
to the Prologix GPIB-USB Controller 6.0: [prologix.biz](http://prologix.biz/)

prologix3.py uses pySerial for the serial driver.

It also includes a simple program which uses it to send a command to an
instrument and read the response.

To use the module, create a *Prologix_USB* object:

`plx = Prologix_USB('/dev/ttyUSB0')`

Then create an Instrument object to talk to a specific instrument:

`ins = plx.instrument(GPIB_ADDRESS)`

Write a command:

`ins.write('*IDN?')`

Read a response:

`response = ins.read()`

Close both:

`ins.close()`
`plx.close()`

In practice it is better to use the SRQ and Poll capabilities of the
interface to synchronise write and read. See sendcmd.py as an example.

# Installation
Use it within the directory that your application sits, or it could be copied to e.g.
*/usr/local/lib/python3.6/dist-files* (or equivalent local Python library on your machine).

I can be contacted at john AT sager DOT me DOT uk

John C Sager
May 2020
