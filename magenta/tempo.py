
# Imports
# Python 2 uses integer division for integers. Using this gives the Python 3
# behavior of producing a float when dividing integers
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from fractions import Fraction
import xml.etree.ElementTree as ET
import zipfile

# internal imports

import six
import magenta.constants


class Tempo(object):
  """Internal representation of a MusicXML tempo."""

  def __init__(self, state, xml_sound=None):
    self.xml_sound = xml_sound
    self.qpm = -1
    self.time_position = -1
    self.xml_position = -1
    self.state = state
    if xml_sound is not None:
      self._parse()

  def _parse(self):
    """Parse the MusicXML <sound> element and retrieve the tempo.

    If no tempo is specified, default to DEFAULT_QUARTERS_PER_MINUTE
    """
    self.qpm = float(self.xml_sound.get('tempo'))
    if self.qpm == 0:
      # If tempo is 0, set it to default
      self.qpm = magenta.constants.DEFAULT_QUARTERS_PER_MINUTE
    self.time_position = self.state.time_position
    self.xml_position = self.state.xml_position

  def __str__(self):
    tempo_str = 'Tempo: ' + str(self.qpm)
    tempo_str += ' (@time: ' + str(self.time_position) + ')'
    return tempo_str

