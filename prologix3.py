"""
   Prologix test interface, severely modified from the code in wanglib
   
   This program is free software; you can redistribute it and/or
   modify it under the terms of the GNU General Public License
   as published by the Free Software Foundation; either version 2
   of the License, or (at your option) any later version.
  
   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
  
   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
   Or, point your browser to:
   http://www.gnu.org/licenses/old-licenses/gpl-2.0.html
   
   The author can be contacted at john at sager dot me dot uk

   Mostly copyright John C Sager 2018-2020
   
   The class 'Serial' and show_newlines are originally from prologix.py
   in Wanglib: https://github.com/baldwint/wanglib.git but Serial is
   significantly modified and the classes Prologix_USB and Instrument
   are new.
   
   THis has now been modified significantly for Python3. pySerial now
   reads and writes byte arrays, but IEEE-488 uses text for most I/O
   so the general purpose read and write routines encode/decode to UTF-8.
   Two raw read & write routines are added to support the '#' data I/O
   
   20200504 - fixed again to do esc-stuffing on write
"""

import sys

if sys.version_info.major < 3:
  raise Exception('You must use Python 3 for prologix3')

import serial, logging
from time import sleep, time, ctime

# show_newlines and Serial are copied & modified from wanglib.util

def show_newlines(string):
  """
  replace CR+LF with the words "CR" and "LF".
  useful for debugging.

  """
  return string.replace('\r', '<CR>').replace('\n', '<LF>')

class Serial(serial.Serial):
  """
  Extension of PySerial_'s :class:`serial.Serial` class that
  implements a few extra features:

  .. _PySerial: http://pyserial.sourceforge.net/

    - an :meth:`ask` method
    - a :meth:`readall` method
    - auto-appended termination characters
    - in/out logging.

  To log whatever's written or read to a serial port,
  pass a filename into the ``log`` kwarg:

  >>> port = Serial('/dev/ttyS0', log='wtf.log')

    
  Python3: read and write data is now bytearrays. These are now expected
  and returned. Added raw_write() and raw_read(), and the main read and
  write routines call them and encode/decode appropriately.

  """

  def __init__(self, *args, **kwargs):
    self.logging = False
    # take 'log' kwarg.
    self.logfile = kwargs.pop('log', None)
    if self.logfile:
      self.logging = True
      # make an event logger
      self.logger = logging.getLogger('prologix.Serial')
      self.start_logging(self.logfile)
    # hand off to standard serial init function
    super(Serial, self).__init__(*args, **kwargs)

  def start_logging(self, fname):
    """ start logging read/write data to file. """
    # make log file handler
    lfh = logging.FileHandler(fname)
    self.logger.addHandler(lfh)
    # make log file formatter
    lff = logging.Formatter('%(asctime)s %(message)s')
    lfh.setFormatter(lff)
    # set level low to log everything
    self.logger.setLevel(1)
    self.logger.debug('opened serial port')

  def raw_write(self, data):
    ''' data is a byte array at this point '''
    super(Serial, self).write(data)
    if self.logging:
      self.logger.debug(' write: ' + show_newlines(data.decode()))

  def raw_read(self, size=1024):
    resp = super(Serial, self).read(size)
    if self.logging:
      self.logger.debug('  read: ' + show_newlines(resp.decode()))
    return resp

  def write(self, data):
    self.raw_write(data.encode())

  def read(self, size=1024):
    return self.raw_read(size).decode()

  def readline(self):
    resp = super(Serial, self).readline().decode()
    if self.logging:
      self.logger.debug('readln: ' + show_newlines(resp))
    return resp

ESC = 27 # for escape-stuffing

class Prologix_USB(object):
  """ 
  This class represents the Prologix adapter and encapsulates the
  gory details of interacting with the adapter.
  Instantiate an object to talk to the adapter:
  
  plx = Prologix_USB(USB_DEVICE)
  
  Then for each instrument, instantiate an object to converse with
  that particular instrument:
  
  ins = plx.instrument(GBIB_ADDRESS)
  
  Then use the methods of class 'Instrument' to converse with it.
  """
  

  def __init__(self, port='/dev/ttyUSBgpib', auto=False, log=False,
      delay=0.2, read_term='', write_term='\n'):
    self.port = port
    self.auto = auto
    self.log = log
    self.delay = delay
    self.read_term = read_term
    self.write_term = write_term
    # current address is kept in this controller instance
    self.address = int(12)
    self.timeout = int(100) # milliseconds
    # characters that must be escaped in data to instrument
    self.escape_set = frozenset((ord('\n'),ord('\r'),ESC,ord('+')))
    
    self.bus = Serial(port, baudrate=115200, rtscts=1, log=log, timeout=0)
    
#    self.bus.readall() # flush buffer
    
    self.writeprologix('++savecfg 0') # don't save config on Prologix
    self.writeprologix('++mode 1') # become a controller
    self.writeprologix('++eos 3') # add nothing on write
    self.writeprologix('++eoi 1') # assert EOI at the end of each command
    if self.read_term != '':
      self.writeprologix('++eot_char %d' % ord(self.read_term)) # append this to instrument responses
      self.writeprologix('++eot_enable 1') # enable eot function
    else:
      self.writeprologix('++eot_enable 0') # disable eot function
    self.writeprologix('++read_tmo_ms %d' % self.timeout)
    self.writeprologix('++addr %d' % self.address)
  
  def set_addr(self,addr): # assumes addr already cast to int
    if addr != self.address:
      self.address = addr
      self.writeprologix('++addr %d' % self.address)

  def esc_stuff(self,data, termch):
    ''' This is needed to escape certain characters '''
    d = []
    for i in range(len(data)):
      x = data[i]
      if not isinstance(x,int):
        x = ord(x)
      if x in self.escape_set:
        d.append(ESC)
      d.append(x)
    out = bytes(d)
    if termch:
      out = out + termch.encode()
    return out

  def read(self, size=1024):
    self.writeprologix('++read eoi')
    sleep(self.delay)
    return self.bus.read(size)

  def readline(self):
    self.writeprologix('++read eoi')
    sleep(self.delay)
    return self.bus.readline()

  def readprologix(self):
#    sleep(self.delay)
    sleep(0.05)
    return self.bus.read()

  def writeprologix(self, command):
    self.bus.write(command+self.write_term)

  def write(self, command):
    # esc-stuff & add term char
    d = self.esc_stuff(command, self.write_term)
    self.bus.raw_write(d)

  def raw_write(self, data):
    # esc-stuff but no term char - actually need to add it for HP54121T
    d = self.esc_stuff(data, self.write_term)
    self.bus.raw_write(d)

  def raw_read(self, size=1024):
    self.bus.write('++read eoi')
    sleep(self.delay)
    return self.bus.raw_read(size)

  def close(self):
    self.bus.close()


  def instrument(self, addr):
    return Instrument(self,addr)



class Instrument(object):
  """
  This class represents an instrument that can be controlled via the
  Prologix adapter. It is instantiated via the method 'instrument()' in
  the Prologix_USB class.
  """

  def __init__(self,port,addr):
    self.port = port
    self.addr = int(addr)
      
  def read(self):
    self.port.set_addr(self.addr)
    return self.port.read()
  
  def readline(self):
    self.port.set_addr(self.addr)
    return self.port.readline()
  
  def write(self, command):
    self.port.set_addr(self.addr)
    self.port.writeprologix('++auto 0')
    self.port.write(command)

  def raw_read(self):
    self.port.set_addr(self.addr)
    return self.port.raw_read()

  def block_read(self):
    self.port.set_addr(self.addr)
    s = self.port.read(2) # read '#[1-9]'
    if s[0] != '#': # not expected format
      return b''
    n = int(s[1]) # number of decimal digits to follow
    l = int(self.port.read(n)) # read n digits as int
    buf = self.port.raw_read(l) # read l bytes as block data
    self.port.raw_read(1) # newline terminator we don't want
    return buf

  def block_write(self, command, data):
    s = str(len(data))
    b = (command+' #'+str(len(s))+s).encode()+data
    self.port.raw_write(b)
    
  def ask_wait(self, command):
    count=0
    self.port.set_addr(self.addr)
    self.port.writeprologix('++auto 0')
    self.port.write(command)
    srq = self.get_srq()
    while srq == '0' and count < 200:
      count += 1
      sleep(0.1)
      srq = self.get_srq()
    return self.port.read()

  def read_wait(self):
    self.port.set_addr(self.addr)
    s = self.port.read()
    while len(s) == 0:
      sleep(0.1)
      s = self.port.read()
    return s
    
  def get_srq(self):
    self.port.set_addr(self.addr)
    self.port.writeprologix('++srq')
    return self.port.readprologix().rstrip()

  def spoll(self):
    self.port.set_addr(self.addr)
    self.port.writeprologix('++spoll %d' % self.addr)
    return self.port.readprologix().rstrip()

  def to_local(self):
    self.port.set_addr(self.addr)
    self.port.writeprologix('++loc')

  def close(self):
    self.to_local()


