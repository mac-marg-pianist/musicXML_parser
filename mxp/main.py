"""MusicXML parser.
"""

# Imports
# Python 2 uses integer division for integers. Using this gives the Python 3
# behavior of producing a float when dividing integers
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from fractions import Fraction
import xml.etree.ElementTree as ET
import zipfile
import math
from .exception import MusicXMLParseException, MultipleTimeSignatureException

# internal imports

import six
from . import constants

from .measure import Measure
from .tempo import Tempo
from .key_signature import KeySignature
from .score_part import ScorePart
from .part import Part

DEFAULT_MIDI_PROGRAM = 0  # Default MIDI Program (0 = grand piano)
DEFAULT_MIDI_CHANNEL = 0  # Default MIDI Channel (0 = first channel)
MUSICXML_MIME_TYPE = 'application/vnd.recordare.musicxml+xml'


class MusicXMLParserState(object):
  """Maintains internal state of the MusicXML parser."""

  def __init__(self):
    # Default to one division per measure
    # From the MusicXML documentation: "The divisions element indicates
    # how many divisions per quarter note are used to indicate a note's
    # duration. For example, if duration = 1 and divisions = 2,
    # this is an eighth note duration."
    self.divisions = 1

    # Default to a tempo of 120 quarter notes per minute
    # MusicXML calls this tempo, but mxp calls this qpm
    # Therefore, the variable is called qpm, but reads the
    # MusicXML tempo attribute
    # (120 qpm is the default tempo according to the
    # Standard MIDI Files 1.0 Specification)
    self.qpm = 120

    # Duration of a single quarter note in seconds
    self.seconds_per_quarter = 0.5

    # Running total of time for the current event in seconds.
    # Resets to 0 on every part. Affected by <forward> and <backup> elements
    self.time_position = 0
    self.xml_position = 0

    # Default to a MIDI velocity of 64 (mf)
    self.velocity = 64

    # Default MIDI program (0 = grand piano)
    self.midi_program = DEFAULT_MIDI_PROGRAM

    # Current MIDI channel (usually equal to the part number)
    self.midi_channel = DEFAULT_MIDI_CHANNEL

    # Keep track of previous note to get chord timing correct
    # This variable stores an instance of the Note class (defined below)
    self.previous_note = None

    # Keep track of previous direction
    self.previous_direction = None

    # Keep track of current transposition level in +/- semitones.
    self.transpose = 0

    # Keep track of current time signature. Does not support polymeter.
    self.time_signature = None

    # Keep track of previous (unsolved) grace notes
    self.previous_grace_notes = []

    # Keep track of chord index
    self.chord_index = 0

    # Keep track of measure number
    self.measure_number = 0

    # Keep track of unsolved ending bracket
    self.first_ending_discontinue = False

    # Keep track of beam status
    self.is_beam_start = False
    self.is_beam_continue = False
    self.is_beam_stop = False



class MusicXMLDocument(object):
  """Internal representation of a MusicXML Document.

  Represents the top level object which holds the MusicXML document
  Responsible for loading the .xml or .mxl file using the _get_score method
  If the file is .mxl, this class uncompresses it

  After the file is loaded, this class then parses the document into memory
  using the parse method.
  """

  def __init__(self, filename):
    self._score = self._get_score(filename)
    self.parts = []
    # ScoreParts indexed by id.
    self._score_parts = {}
    self.midi_resolution = constants.STANDARD_PPQ
    self._state = MusicXMLParserState()
    # Total time in seconds
    self.total_time_secs = 0
    self.total_time_duration = 0
    self._parse()
    self._recalculate_time_position()

  @staticmethod
  def _get_score(filename):
    """Given a MusicXML file, return the score as an xml.etree.ElementTree.

    Given a MusicXML file, return the score as an xml.etree.ElementTree
    If the file is compress (ends in .mxl), uncompress it first

    Args:
        filename: The path of a MusicXML file

    Returns:
      The score as an xml.etree.ElementTree.

    Raises:
      MusicXMLParseException: if the file cannot be parsed.
    """
    score = None
    if filename.endswith('.mxl'):
      # Compressed MXL file. Uncompress in memory.
      try:
        mxlzip = zipfile.ZipFile(filename)
      except zipfile.BadZipfile as exception:
        raise MusicXMLParseException(exception)

      # A compressed MXL file may contain multiple files, but only one
      # MusicXML file. Read the META-INF/container.xml file inside of the
      # MXL file to locate the MusicXML file within the MXL file
      # http://www.musicxml.com/tutorial/compressed-mxl-files/zip-archive-structure/

      # Raise a MusicXMLParseException if multiple MusicXML files found

      infolist = mxlzip.infolist()
      if six.PY3:
        # In py3, instead of returning raw bytes, ZipFile.infolist() tries to
        # guess the filenames' encoding based on file headers, and decodes using
        # this encoding in order to return a list of strings. If the utf-8
        # header is missing, it decodes using the DOS code page 437 encoding
        # which is almost definitely wrong. Here we need to explicitly check
        # for when this has occurred and change the encoding to utf-8.
        # https://stackoverflow.com/questions/37723505/namelist-from-zipfile-returns-strings-with-an-invalid-encoding
        zip_filename_utf8_flag = 0x800
        for info in infolist:
          if info.flag_bits & zip_filename_utf8_flag == 0:
            filename_bytes = info.filename.encode('437')
            filename = filename_bytes.decode('utf-8', 'replace')
            info.filename = filename

      container_file = [x for x in infolist
                        if x.filename == 'META-INF/container.xml']
      compressed_file_name = ''

      if container_file:
        try:
          container = ET.fromstring(mxlzip.read(container_file[0]))
          for rootfile_tag in container.findall('./rootfiles/rootfile'):
            if 'media-type' in rootfile_tag.attrib:
              if rootfile_tag.attrib['media-type'] == MUSICXML_MIME_TYPE:
                if not compressed_file_name:
                  compressed_file_name = rootfile_tag.attrib['full-path']
                else:
                  raise MusicXMLParseException(
                    'Multiple MusicXML files found in compressed archive')
            else:
              # No media-type attribute, so assume this is the MusicXML file
              if not compressed_file_name:
                compressed_file_name = rootfile_tag.attrib['full-path']
              else:
                raise MusicXMLParseException(
                  'Multiple MusicXML files found in compressed archive')
        except ET.ParseError as exception:
          raise MusicXMLParseException(exception)

      if not compressed_file_name:
        raise MusicXMLParseException(
          'Unable to locate main .xml file in compressed archive.')
      if six.PY2:
        # In py2, the filenames in infolist are utf-8 encoded, so
        # we encode the compressed_file_name as well in order to
        # be able to lookup compressed_file_info below.
        compressed_file_name = compressed_file_name.encode('utf-8')
      try:
        compressed_file_info = [x for x in infolist
                                if x.filename == compressed_file_name][0]
      except IndexError:
        raise MusicXMLParseException(
          'Score file %s not found in zip archive' % compressed_file_name)
      score_string = mxlzip.read(compressed_file_info)
      try:
        score = ET.fromstring(score_string)
      except ET.ParseError as exception:
        raise MusicXMLParseException(exception)
    else:
      # Uncompressed XML file.
      try:
        tree = ET.parse(filename)
        score = tree.getroot()
      except ET.ParseError as exception:
        raise MusicXMLParseException(exception)

    return score

  def _parse(self):
    """Parse the uncompressed MusicXML document."""
    # Parse part-list
    xml_part_list = self._score.find('part-list')
    if xml_part_list is not None:
      for element in xml_part_list:
        if element.tag == 'score-part':
          score_part = ScorePart(element)
          self._score_parts[score_part.id] = score_part

    # Parse parts
    for score_part_index, child in enumerate(self._score.findall('part')):
      part = Part(child, self._score_parts, self._state)
      self.parts.append(part)
      score_part_index += 1
      if self._state.time_position > self.total_time_secs:
        self.total_time_secs = self._state.time_position
      if self._state.xml_position > self.total_time_duration:
        self.total_time_duration = self._state.xml_position

  def _recalculate_time_position(self):
    """ Sometimes, the tempo marking is not located in the first voice.
    Therefore, the time position of each object should be calculate after parsing the entire tempo objects.

    """
    tempos = self.get_tempos()

    tempos.sort(key=lambda x: x.xml_position)
    if tempos[0].xml_position != 0:
      default_tempo = Tempo(self._state)
      default_tempo.xml_position = 0
      default_tempo.time_position = 0
      default_tempo.qpm = constants.DEFAULT_QUARTERS_PER_MINUTE
      default_tempo.state.divisions = tempos[0].state.divisions
      tempos.insert(0, default_tempo)
    new_time_position = 0
    for i in range(len(tempos)):
      tempos[i].time_position = new_time_position
      if i + 1 < len(tempos):
        new_time_position += (tempos[i + 1].xml_position - tempos[i].xml_position) / tempos[i].qpm * 60 / tempos[
          i].state.divisions

    for part in self.parts:
      for measure in part.measures:
        for note in measure.notes:
          for i in range(len(tempos)):
            if i + 1 == len(tempos):
              current_tempo = tempos[i].qpm / 60 * tempos[i].state.divisions
              break
            else:
              if tempos[i].xml_position <= note.note_duration.xml_position and tempos[
                i + 1].xml_position > note.note_duration.xml_position:
                current_tempo = tempos[i].qpm / 60 * tempos[i].state.divisions
                break
          note.note_duration.time_position = tempos[i].time_position + (
                  note.note_duration.xml_position - tempos[i].xml_position) / current_tempo
          note.note_duration.seconds = note.note_duration.duration / current_tempo

  def get_chord_symbols(self):
    """Return a list of all the chord symbols used in this score."""
    chord_symbols = []
    for part in self.parts:
      for measure in part.measures:
        for chord_symbol in measure.chord_symbols:
          if chord_symbol not in chord_symbols:
            # Prevent duplicate chord symbols
            chord_symbols.append(chord_symbol)
    return chord_symbols

  def get_time_signatures(self):
    """Return a list of all the time signatures used in this score.

    Does not support polymeter (i.e. assumes all parts have the same
    time signature, such as Part 1 having a time signature of 6/8
    while Part 2 has a simultaneous time signature of 2/4).

    Ignores duplicate time signatures to prevent mxp duplicate
    time signature error. This happens when multiple parts have the
    same time signature is used in multiple parts at the same time.

    Example: If Part 1 has a time siganture of 4/4 and Part 2 also
    has a time signature of 4/4, then only instance of 4/4 is sent
    to mxp.

    Returns:
      A list of all TimeSignature objects used in this score.
    """
    time_signatures = []
    for part in self.parts:
      for measure in part.measures:
        if measure.time_signature is not None:
          if measure.time_signature not in time_signatures:
            # Prevent duplicate time signatures
            time_signatures.append(measure.time_signature)

    return time_signatures

  def get_key_signatures(self):
    """Return a list of all the key signatures used in this score.

    Support different key signatures in different parts (score in
    written pitch).

    Ignores duplicate key signatures to prevent mxp duplicate key
    signature error. This happens when multiple parts have the same
    key signature at the same time.

    Example: If the score is in written pitch and the
    flute is written in the key of Bb major, the trombone will also be
    written in the key of Bb major. However, the clarinet and trumpet
    will be written in the key of C major because they are Bb transposing
    instruments.

    If no key signatures are found, create a default key signature of
    C major.

    Returns:
      A list of all KeySignature objects used in this score.
    """
    key_signatures = []
    for part in self.parts:
      for measure in part.measures:
        if measure.key_signature is not None:
          if measure.key_signature not in key_signatures:
            # Prevent duplicate key signatures
            key_signatures.append(measure.key_signature)

    if not key_signatures:
      # If there are no key signatures, add C major at the beginning
      key_signature = KeySignature(self._state)
      key_signature.time_position = 0
      key_signature.xml_position = 0
      key_signatures.append(key_signature)

    return key_signatures

  def get_tempos(self):
    """Return a list of all tempos in this score.

    If no tempos are found, create a default tempo of 120 qpm.

    Returns:
      A list of all Tempo objects used in this score.
    """
    tempos = []

    if self.parts:
      part = self.parts[0]  # Use only first part
      for measure in part.measures:
        for tempo in measure.tempos:
          tempos.append(tempo)

    # If no tempos, add a default of 120 at beginning
    if not tempos:
      tempo = Tempo(self._state)
      tempo.qpm = self._state.qpm
      tempo.time_position = 0
      tempo.xml_position = 0
      tempos.append(tempo)

    return tempos

  def get_measure_positions(self):
    part = self.parts[0]
    measure_positions = []

    for measure in part.measures:
      measure_positions.append(measure.start_xml_position)

    return measure_positions


  def get_notes(self, melody_only=False, grace_note=True):
    notes = []
    previous_grace_notes = []
    rests = []
    num_parts = len(self.parts)
    for instrument_index in range(num_parts):
      part = self.parts[instrument_index]
      measure_number = 1
      for measure in part.measures:
        for note in measure.notes:
          note.measure_number = measure_number
          note.voice += instrument_index * 10
          if melody_only:
            if note.voice == 1:
              notes, previous_grace_notes, rests = self.check_note_status_and_append(note, notes, previous_grace_notes,
                                                                                rests, grace_note)
          else:
            notes, previous_grace_notes, rests = self.check_note_status_and_append(note, notes, previous_grace_notes, rests,
                                                                              grace_note)

        measure_number += 1
      notes = self.apply_after_grace_note_to_chord_notes(notes)
      if melody_only:
        notes = self.delete_chord_notes_for_melody(notes)
      notes = self.apply_tied_notes(notes)
      notes.sort(key=lambda x: (x.note_duration.xml_position, x.note_duration.grace_order, -x.pitch[1]))
      notes = self.check_overlapped_notes(notes)
      notes = self.apply_rest_to_note(notes, rests)
      notes = self.omit_trill_notes(notes)
      notes = self.extract_and_apply_slurs(notes)
      # notes = self.rearrange_chord_index(notes)

    return notes

  def apply_tied_notes(self, xml_notes):
    tie_clean_list = []
    for i in range(len(xml_notes)):
      if xml_notes[i].note_notations.tied_stop == False:
        tie_clean_list.append(xml_notes[i])
      else:
        for j in reversed(range(len(tie_clean_list))):
          if tie_clean_list[j].note_notations.tied_start and tie_clean_list[j].pitch[1] == xml_notes[i].pitch[1]:
            tie_clean_list[j].note_duration.seconds += xml_notes[i].note_duration.seconds
            tie_clean_list[j].note_duration.duration += xml_notes[i].note_duration.duration
            tie_clean_list[j].note_duration.midi_ticks += xml_notes[i].note_duration.midi_ticks
            if xml_notes[i].note_notations.slurs:
              for slur in xml_notes[i].note_notations.slurs:
                tie_clean_list[j].note_notations.slurs.append(slur)
            break
    return tie_clean_list

  def omit_trill_notes(self, xml_notes):
    num_notes = len(xml_notes)
    omit_index = []
    trill_sign = []
    wavy_lines = []
    for i in range(num_notes):
      note = xml_notes[i]
      if not note.is_print_object:
        omit_index.append(i)
        if note.accidental:
          # TODO: handle accidentals in non-print notes
          if note.accidental == 'natural':
            pass
          elif note.accidental == 'sharp':
            pass
          elif note.accidental == 'flat':
            pass
        if note.note_notations.is_trill:
          trill = {'xml_pos': note.note_duration.xml_position, 'pitch': note.pitch[1]}
          trill_sign.append(trill)
      if note.note_notations.wavy_line:
        wavy_line = note.note_notations.wavy_line
        wavy_line.xml_position = note.note_duration.xml_position
        wavy_line.pitch = note.pitch
        wavy_lines.append(wavy_line)

      # move trill mark to the highest notes of the onset
      if note.note_notations.is_trill:
        notes_in_trill_onset = []
        current_position = note.note_duration.xml_position

        search_index = i
        while search_index + 1 < num_notes and xml_notes[
          search_index + 1].note_duration.xml_position == current_position:
          search_index += 1
          notes_in_trill_onset.append(xml_notes[search_index])
        search_index = i

        while search_index - 1 >= 0 and xml_notes[search_index - 1].note_duration.xml_position == current_position:
          search_index -= 1
          notes_in_trill_onset.append(xml_notes[search_index])

        for other_note in notes_in_trill_onset:
          highest_note = note
          if other_note.voice == note.voice and other_note.pitch[1] > highest_note.pitch[
            1] and not other_note.note_duration.is_grace_note:
            highest_note.note_notations.is_trill = False
            other_note.note_notations.is_trill = True

    wavy_lines = self.combine_wavy_lines(wavy_lines)

    for index in reversed(omit_index):
      note = xml_notes[index]
      xml_notes.remove(note)

    if len(trill_sign) > 0:
      for trill in trill_sign:
        for note in xml_notes:
          if note.note_duration.xml_position == trill['xml_pos'] and abs(note.pitch[1] - trill['pitch']) < 4 \
                  and not note.note_duration.is_grace_note:
            note.note_notations.is_trill = True
            break

    xml_notes = self.apply_wavy_lines(xml_notes, wavy_lines)

    return xml_notes

  def check_note_status_and_append(self, note, notes, previous_grace_notes, rests, include_grace_note):
    if note.note_duration.is_grace_note:
      previous_grace_notes.append(note)
      if include_grace_note:
        notes.append(note)
    elif not note.is_rest:
      if len(previous_grace_notes) > 0:
        rest_grc = []
        added_grc = []
        grace_order = -1
        for grc in reversed(previous_grace_notes):
          if grc.voice == note.voice:
            note.note_duration.preceded_by_grace_note = True
            grc.note_duration.grace_order = grace_order
            grc.following_note = note
            if grc.chord_index == 0:
              grace_order -= 1
            added_grc.append(grc)

            # notes.append(grc)
          else:
            rest_grc.append(grc)
        num_added = abs(grace_order) - 1
        for grc in added_grc:
          # grc.note_duration.grace_order /= num_added
          grc.note_duration.num_grace = num_added
          if abs(grc.note_duration.grace_order) == num_added:
            grc.note_duration.is_first_grace_note = True
        previous_grace_notes = rest_grc
      notes.append(note)
    else:
      assert note.is_rest
      if note.is_print_object:
        rests.append(note)

    return notes, previous_grace_notes, rests

  def apply_rest_to_note(self, xml_notes, rests):
    xml_positions = [note.note_duration.xml_position for note in xml_notes]
    # concat continuous rests
    new_rests = []
    num_rests = len(rests)
    for i in range(num_rests):
      rest = rests[i]
      j = 1
      current_end = rest.note_duration.xml_position + rest.note_duration.duration
      current_voice = rest.voice
      while i + j < num_rests - 1:
        next_rest = rests[i + j]
        if next_rest.note_duration.duration == 0:
          break
        if next_rest.note_duration.xml_position == current_end and next_rest.voice == current_voice:
          rest.note_duration.duration += next_rest.note_duration.duration
          next_rest.note_duration.duration = 0
          current_end = rest.note_duration.xml_position + rest.note_duration.duration
          if next_rest.note_notations.is_fermata:
            rest.note_notations.is_fermata = True
        elif next_rest.note_duration.xml_position > current_end:
          break
        j += 1

      if not rest.note_duration.duration == 0:
        new_rests.append(rest)

    rests = new_rests

    for rest in rests:
      rest_position = rest.note_duration.xml_position
      closest_note_index = self.binary_index(xml_positions, rest_position)
      rest_is_fermata = rest.note_notations.is_fermata

      search_index = 0
      while closest_note_index - search_index >= 0:
        prev_note = xml_notes[closest_note_index - search_index]
        if prev_note.voice == rest.voice:
          prev_note_end = prev_note.note_duration.xml_position + prev_note.note_duration.duration
          prev_note_with_rest = prev_note_end + prev_note.following_rest_duration
          if prev_note_end == rest_position:
            prev_note.following_rest_duration = rest.note_duration.duration
            if rest_is_fermata:
              prev_note.followed_by_fermata_rest = True
          elif prev_note_end < rest_position:
            break
        # elif prev_note_with_rest == rest_position and prev_note.voice == rest.voice:
        #     prev_note.following_rest_duration += rest.note_duration.duration
        search_index += 1

    return xml_notes

  def apply_after_grace_note_to_chord_notes(self, notes):
    for note in notes:
      if note.note_duration.preceded_by_grace_note:
        onset = note.note_duration.xml_position
        voice = note.voice
        chords = self.find(
          lambda x: x.note_duration.xml_position == onset and x.voice == voice and not x.note_duration.is_grace_note,
          notes)
        for chd in chords:
          chd.note_duration.preceded_by_grace_note = True
    return notes

  def delete_chord_notes_for_melody(self, melody_notes):
    note_onset_positions = list(set(note.note_duration.xml_position for note in melody_notes))
    note_onset_positions.sort()
    unique_melody = []
    for onset in note_onset_positions:
      notes = self.find(lambda x: x.note_duration.xml_position == onset, melody_notes)
      if len(notes) == 1:
        unique_melody.append(notes[0])
      else:
        notes.sort(key=lambda x: x.pitch[1])
        unique_melody.append(notes[-1])

    return unique_melody

  def find(self, f, seq):
    items_list = []
    for item in seq:
      if f(item):
        items_list.append(item)
    return items_list

  def apply_wavy_lines(self, xml_notes, wavy_lines):
    xml_positions = [x.note_duration.xml_position for x in xml_notes]
    num_notes = len(xml_notes)
    omit_indices = []
    for wavy in wavy_lines:
      index = self.binary_index(xml_positions, wavy.xml_position)
      while abs(xml_notes[index].pitch[1] - wavy.pitch[1]) > 3 and index > 0 \
              and xml_notes[index - 1].note_duration.xml_position == xml_notes[index].note_duration.xml_position:
        index -= 1
      note = xml_notes[index]
      wavy_duration = wavy.end_xml_position - wavy.xml_position
      note.note_duration.duration = wavy_duration
      trill_pitch = note.pitch[1]
      next_idx = index + 1
      while next_idx < num_notes and xml_notes[next_idx].note_duration.xml_position < wavy.end_xml_position:
        if xml_notes[next_idx].pitch[1] == trill_pitch:
          omit_indices.append(next_idx)
        next_idx += 1

    omit_indices.sort()
    if len(omit_indices) > 0:
      for idx in reversed(omit_indices):
        del xml_notes[idx]

    return xml_notes

  def check_overlapped_notes(self, xml_notes):
    previous_onset = -1
    notes_on_onset = []
    pitches = []
    for note in xml_notes:
      if note.note_duration.is_grace_note:
        continue  # does not count grace note, because it can have same pitch on same xml_position
      if note.note_duration.xml_position > previous_onset:
        previous_onset = note.note_duration.xml_position
        pitches = []
        pitches.append(note.pitch[1])
        notes_on_onset = []
        notes_on_onset.append(note)
      else:  # note has same xml_position
        if note.pitch[1] in pitches:  # same pitch with same
          index_of_same_pitch_note = pitches.index(note.pitch[1])
          previous_note = notes_on_onset[index_of_same_pitch_note]
          if previous_note.note_duration.duration > note.note_duration.duration:
            note.is_overlapped = True
          else:
            previous_note.is_overlapped = True
        else:
          pitches.append(note.pitch[1])
          notes_on_onset.append(note)

    return xml_notes

  def combine_wavy_lines(self, wavy_lines):
    num_wavy = len(wavy_lines)
    for i in reversed(range(num_wavy)):
      wavy = wavy_lines[i]
      if wavy.type == 'stop':
        deleted = False
        for j in range(1, i + 1):
          prev_wavy = wavy_lines[i - j]
          if prev_wavy.type == 'start' and prev_wavy.number == wavy.number:
            prev_wavy.end_xml_position = wavy.xml_position
            wavy_lines.remove(wavy)
            deleted = True
            break
        if not deleted:
          wavy_lines.remove(wavy)
    num_wavy = len(wavy_lines)
    for i in reversed(range(num_wavy)):
      wavy = wavy_lines[i]
      if wavy.type == 'start' and wavy.end_xml_position == 0:
        wavy_lines.remove(wavy)
    return wavy_lines

  def extract_and_apply_slurs(self, xml_notes):
    resolved_slurs = []
    unresolved_slurs = []
    slur_index = 0
    for note in xml_notes:
      slurs = note.note_notations.slurs
      if slurs:
        for slur in reversed(slurs):
          slur.xml_position = note.note_duration.xml_position
          slur.voice = note.voice
          type = slur.type
          if type == 'start':
            slur.index = slur_index
            unresolved_slurs.append(slur)
            slur_index += 1
            note.note_notations.is_slur_start = True
          elif type == 'stop':
            note.note_notations.is_slur_stop = True
            for prev_slur in unresolved_slurs:
              if prev_slur.number == slur.number and prev_slur.voice == slur.voice:
                prev_slur.end_xml_position = slur.xml_position
                resolved_slurs.append(prev_slur)
                unresolved_slurs.remove(prev_slur)
                note.note_notations.slurs.remove(slur)
                note.note_notations.slurs.append(prev_slur)
                break

    for note in xml_notes:
      slurs = note.note_notations.slurs
      note_position = note.note_duration.xml_position
      if not slurs:
        for prev_slur in resolved_slurs:
          if prev_slur.voice == note.voice and prev_slur.xml_position <= note_position <= prev_slur.end_xml_position:
            note.note_notations.slurs.append(prev_slur)
            if prev_slur.xml_position == note_position:
              note.note_notations.is_slur_start = True
            elif prev_slur.end_xml_position == note_position:
              note.note_notations.is_slur_stop = True
            else:
              note.note_notations.is_slur_continue = True

    return xml_notes


  def rearrange_chord_index(self, xml_notes):
    # assert all(xml_notes[i].pitch[1] >= xml_notes[i + 1].pitch[1] for i in range(len(xml_notes) - 1)
    #            if xml_notes[i].note_duration.xml_position ==xml_notes[i+1].note_duration.xml_position)

    previous_position = [-1]
    max_chord_index = [0]
    for note in xml_notes:
      voice = note.voice - 1
      while voice >= len(previous_position):
        previous_position.append(-1)
        max_chord_index.append(0)
      if note.note_duration.is_grace_note:
        continue
      if note.staff == 1:
        if note.note_duration.xml_position > previous_position[voice]:
          previous_position[voice] = note.note_duration.xml_position
          max_chord_index[voice] = note.chord_index
          note.chord_index = 0
        else:
          note.chord_index = (max_chord_index[voice] - note.chord_index)
      else:  # note staff ==2
        pass

    return xml_notes

  def get_directions(self):
    directions = []
    for part in self.parts:
        for measure in part.measures:
            for direction in measure.directions:
                directions.append(direction)

    directions.sort(key=lambda x: x.xml_position)
    cleaned_direction = []
    for i in range(len(directions)):
        dir = directions[i]
        if not dir.type == None:
            if dir.type['type'] == "none":
                for j in range(i):
                    prev_dir = directions[i-j-1]
                    if 'number' in prev_dir.type.keys():
                        prev_key = prev_dir.type['type']
                        prev_num = prev_dir.type['number']
                    else:
                        continue
                    if prev_num == dir.type['number']:
                        if prev_key == "crescendo":
                            dir.type['type'] = 'crescendo'
                            break
                        elif prev_key == "diminuendo":
                            dir.type['type'] = 'diminuendo'
                            break
            cleaned_direction.append(dir)
        else:
            print(vars(dir.xml_direction))

    return cleaned_direction

  def get_beat_positions(self, in_measure_level=False):
    piano = self.parts[0]
    num_measure = len(piano.measures)
    time_signatures = self.get_time_signatures()
    time_sig_position = [time.xml_position for time in time_signatures]
    beat_piece = []
    for i in range(num_measure):
      measure = piano.measures[i]
      measure_start = measure.start_xml_position
      corresp_time_sig_idx = self.binary_index(time_sig_position, measure_start)
      corresp_time_sig = time_signatures[corresp_time_sig_idx]
      # corresp_time_sig = measure.time_signature
      full_measure_length = corresp_time_sig.state.divisions * corresp_time_sig.numerator / corresp_time_sig.denominator * 4
      if i < num_measure - 1:
        actual_measure_length = piano.measures[i + 1].start_xml_position - measure_start
      else:
        actual_measure_length = full_measure_length

      # if i +1 < num_measure:
      #     measure_length = piano.measures[i+1].start_xml_position - measure_start
      # else:
      #     measure_length = measure_start - piano.measures[i-1].start_xml_position

      num_beat_in_measure = corresp_time_sig.numerator
      if in_measure_level:
        num_beat_in_measure = 1
      elif num_beat_in_measure == 6:
        num_beat_in_measure = 2
      elif num_beat_in_measure == 9:
        num_beat_in_measure = 3
      elif num_beat_in_measure == 12:
        num_beat_in_measure = 4
      elif num_beat_in_measure == 18:
        num_beat_in_measure = 3
      elif num_beat_in_measure == 24:
        num_beat_in_measure = 4
      inter_beat_interval = full_measure_length / num_beat_in_measure
      if actual_measure_length != full_measure_length:
        measure.implicit = True

      if measure.implicit:
        current_measure_length = piano.measures[i + 1].start_xml_position - measure_start
        length_ratio = current_measure_length / full_measure_length
        minimum_beat = 1 / num_beat_in_measure
        num_beat_in_measure = int(math.ceil(length_ratio / minimum_beat))
        if i == 0:
          for j in range(-num_beat_in_measure, 0):
            beat = piano.measures[i + 1].start_xml_position + j * inter_beat_interval
            if len(beat_piece) > 0 and beat > beat_piece[-1]:
              beat_piece.append(beat)
            elif len(beat_piece) == 0:
              beat_piece.append(beat)
        else:
          for j in range(0, num_beat_in_measure):
            beat = piano.measures[i].start_xml_position + j * inter_beat_interval
            if beat > beat_piece[-1]:
              beat_piece.append(beat)
      else:
        for j in range(num_beat_in_measure):
          beat = measure_start + j * inter_beat_interval
          beat_piece.append(beat)
        #
      # for note in measure.notes:
      #     note.on_beat = check_note_on_beat(note, measure_start, measure_length)
    return beat_piece


  def binary_index(self, alist, item):
    first = 0
    last = len(alist)-1
    midpoint = 0

    if(item< alist[first]):
        return 0

    while first<last:
        midpoint = (first + last)//2
        currentElement = alist[midpoint]

        if currentElement < item:
            if alist[midpoint+1] > item:
                return midpoint
            else: first = midpoint +1
            if first == last and alist[last] > item:
                return midpoint
        elif currentElement > item:
            last = midpoint -1
        else:
            if midpoint +1 ==len(alist):
                return midpoint
            while alist[midpoint+1] == item:
                midpoint += 1
                if midpoint + 1 == len(alist):
                    return midpoint
            return midpoint
    return last
