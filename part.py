from mxp.measure import Measure
from mxp.score_part import ScorePart
import xml.etree.ElementTree as ET

class Part(object):
  """Internal represention of a MusicXML <part> element."""

  def __init__(self, xml_part, score_parts, state):
    self.id = ''
    self.score_part = None
    self.measures = []
    self._state = state
    self._parse(xml_part, score_parts)

  def _parse(self, xml_part, score_parts):
    """Parse the <part> element."""
    if 'id' in xml_part.attrib:
      self.id = xml_part.attrib['id']
    if self.id in score_parts:
      self.score_part = score_parts[self.id]
    else:
      # If this part references a score-part id that was not found in the file,
      # construct a default score-part.
      self.score_part = ScorePart()

    # Reset the time position when parsing each part
    self._state.time_position = 0
    self._state.xml_position = 0
    self._state.midi_channel = self.score_part.midi_channel
    self._state.midi_program = self.score_part.midi_program
    self._state.transpose = 0

    xml_measures = xml_part.findall('measure')
    for measure in xml_measures:
      # Issue #674: Repair measures that do not contain notes
      # by inserting a whole measure rest
      self._repair_empty_measure(measure)
      parsed_measure = Measure(measure, self._state)
      self.measures.append(parsed_measure)

  def _repair_empty_measure(self, measure):
    """Repair a measure if it is empty by inserting a whole measure rest.

    If a <measure> only consists of a <forward> element that advances
    the time cursor, remove the <forward> element and replace
    with a whole measure rest of the same duration.

    Args:
      measure: The measure to repair.
    """
    # Issue #674 - If the <forward> element is in a measure without
    # any <note> elements, treat it as if it were a whole measure
    # rest by inserting a rest of that duration
    forward_count = len(measure.findall('forward'))
    note_count = len(measure.findall('note'))
    if note_count == 0 and forward_count == 1:
      # Get the duration of the <forward> element
      xml_forward = measure.find('forward')
      xml_duration = xml_forward.find('duration')
      forward_duration = int(xml_duration.text)

      # Delete the <forward> element
      measure.remove(xml_forward)

      # Insert the new note
      new_note = '<note>'
      new_note += '<rest /><duration>' + str(forward_duration) + '</duration>'
      new_note += '<voice>1</voice><type>whole</type><staff>1</staff>'
      new_note += '</note>'
      new_note_xml = ET.fromstring(new_note)
      measure.append(new_note_xml)

  def __str__(self):
    part_str = 'Part: ' + self.score_part.part_name
    return part_str
