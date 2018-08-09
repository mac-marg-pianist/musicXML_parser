from fractions import Fraction
import xml.etree.ElementTree as ET
import zipfile
from mxp.exception import UnpitchedNoteException, PitchStepParseException
from mxp.notations import Notations
from mxp.note_duration import NoteDuration
from mxp.note_dynamic import NoteDynamic
from mxp.note_dynamic import NoteTempo

import copy


class Note(object):
    """Internal representation of a MusicXML <note> element."""

    def __init__(self, xml_note, state):
        self.xml_note = xml_note
        self.voice = 1
        self.is_rest = False
        self.is_in_chord = False
        # Note.is_grace_note is use to calculate NoteDuration of grace note.
        # Therefore, use NoteDuration.is_grace_note.
        self.is_grace_note = False
        self.pitch = None  # Tuple (Pitch Name, MIDI number)
        self.note_duration = NoteDuration(state)
        self.state_fixed = copy.copy(state)
        self.state = state
        self.note_notations = Notations()
        self.dynamic = NoteDynamic()
        self.tempo = NoteTempo()
        self._parse()
        self.staff = 1

    def _parse(self):
        """Parse the MusicXML <note> element."""

        self.midi_channel = self.state.midi_channel
        self.midi_program = self.state.midi_program
        self.velocity = self.state.velocity

        for child in self.xml_note:
            if child.tag == 'chord':
                self.is_in_chord = True
            elif child.tag == 'duration':  # if the note is_grace_note, the note does not have 'duration' child.
                self.note_duration.parse_duration(self.is_in_chord, self.is_grace_note, child.text)
                # if len(self.state.previous_grace_notes) > 0:
                #   self.apply_previous_grace_notes()
            elif child.tag == 'pitch':
                self._parse_pitch(child)
            elif child.tag == 'rest':
                self.is_rest = True
            elif child.tag == 'voice':
                self.voice = int(child.text)
            elif child.tag == 'dot':
                self.note_duration.dots += 1
            elif child.tag == 'type':
                self.note_duration.type = child.text
            elif child.tag == 'time-modification':
                # A time-modification element represents a tuplet_ratio
                self._parse_tuplet(child)
            elif child.tag == 'notations':
                self.note_notations.parse_notations(child)
            elif child.tag == 'unpitched':
                raise UnpitchedNoteException('Unpitched notes are not supported')
            elif child.tag == 'grace':
                self.note_duration.parse_duration(self.is_in_chord, True, 0)
                self.state.previous_grace_notes.append(self)
            elif child.tag == 'staff':
                self.staff = int(child.text)
            else:
                # Ignore other tag types because they are not relevant to mxp.
                pass

    def _parse_pitch(self, xml_pitch):
        """Parse the MusicXML <pitch> element."""
        step = xml_pitch.find('step').text
        alter_text = ''
        alter = 0.0
        if xml_pitch.find('alter') is not None:
            alter_text = xml_pitch.find('alter').text
        octave = xml_pitch.find('octave').text

        # Parse alter string to a float (floats represent microtonal alterations)
        if alter_text:
            alter = float(alter_text)

        # Check if this is a semitone alter (i.e. an integer) or microtonal (float)
        alter_semitones = int(alter)  # Number of semitones
        is_microtonal_alter = (alter != alter_semitones)

        # Visual pitch representation
        alter_string = ''
        if alter_semitones == -2:
            alter_string = 'bb'
        elif alter_semitones == -1:
            alter_string = 'b'
        elif alter_semitones == 1:
            alter_string = '#'
        elif alter_semitones == 2:
            alter_string = 'x'

        if is_microtonal_alter:
            alter_string += ' (+microtones) '

        # N.B. - pitch_string does not account for transposition
        pitch_string = step + alter_string + octave

        # Compute MIDI pitch number (C4 = 60, C1 = 24, C0 = 12)
        midi_pitch = self.pitch_to_midi_pitch(step, alter, octave)
        # Transpose MIDI pitch
        midi_pitch += self.state.transpose
        self.pitch = (pitch_string, midi_pitch)

    def _parse_tuplet(self, xml_time_modification):
        """Parses a tuplet ratio.

    Represented in MusicXML by the <time-modification> element.

    Args:
      xml_time_modification: An xml time-modification element.
    """
        numerator = int(xml_time_modification.find('actual-notes').text)
        denominator = int(xml_time_modification.find('normal-notes').text)
        self.note_duration.tuplet_ratio = Fraction(numerator, denominator)

    @staticmethod
    def pitch_to_midi_pitch(step, alter, octave):
        """Convert MusicXML pitch representation to MIDI pitch number."""
        pitch_class = 0
        if step == 'C':
            pitch_class = 0
        elif step == 'D':
            pitch_class = 2
        elif step == 'E':
            pitch_class = 4
        elif step == 'F':
            pitch_class = 5
        elif step == 'G':
            pitch_class = 7
        elif step == 'A':
            pitch_class = 9
        elif step == 'B':
            pitch_class = 11
        else:
            # Raise exception for unknown step (ex: 'Q')
            raise PitchStepParseException('Unable to parse pitch step ' + step)
        pitch_class = (pitch_class + int(alter))
        midi_pitch = (12 + pitch_class) + (int(octave) * 12)
        return midi_pitch

    def __str__(self):
        note_string = '{duration: ' + str(self.note_duration.duration)
        note_string += ', midi_ticks: ' + str(self.note_duration.midi_ticks)
        note_string += ', seconds: ' + str(self.note_duration.seconds)
        if self.is_rest:
            note_string += ', rest: ' + str(self.is_rest)
        else:
            note_string += ', pitch: ' + self.pitch[0]
            note_string += ', MIDI pitch: ' + str(self.pitch[1])

        note_string += ', voice: ' + str(self.voice)
        note_string += ', velocity: ' + str(self.velocity) + '} '
        note_string += '(@time: ' + str(self.note_duration.time_position) + ')'
        return note_string

        pass

    def apply_previous_grace_notes(self):
        num_grace = 0
        corresp_grace = []
        for grc in self.state.previous_grace_notes:
            if grc.voice == self.voice:
                num_grace += 1
                corresp_grace.append(grc)

        total_seconds_grace = 0
        for grc in corresp_grace:
            temp_duration_grace = self.state.divisions / 8
            print(temp_duration_grace)
            if temp_duration_grace * num_grace > self.note_duration.duration / 2:
                temp_duration_grace = self.note_duration.duration / 2 / num_grace
            grc.note_duration.time_position += total_seconds_grace
            grc.note_duration.seconds = temp_duration_grace * self.state.seconds_per_quarter
            total_seconds_grace += grc.note_duration.seconds
        print(total_seconds_grace)
        self.note_duration.time_position += -total_seconds_grace
        self.state.previous_grace_notes = []
        print(self)
