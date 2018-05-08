import pretty_midi
import warnings
import numpy as np


ONSET_DURATION = 0.032


class SustainPedal:
    """A sustain_pedal event.
    Parameters
    ----------
    number : int
        control number. {64, 127}
    value : int
        The value of the control change, in [0, 127].
    start, end : float or None
        Time where the control change occurs.
    """

    def __init__(self, start, end, value, number):
        self.number = number
        self.value = value
        self.start = start
        self.end = end

    def __repr__(self):
        return ('Sustain_Pedal (start={:f}, end={:f}, value={:d},  number={:d}'
                .format(self.start, self.end, self.value, self.number))

    def is_valid(self):
        return self.end is not None and self.end > self.start


def elongate_offset_by_pedal(midi_obj):
    """elongate off set of notes in midi_object, according to sustain pedal length.

    :param
        midi_obj: pretty_midi.PrettyMIDI object
    :return:
        pretty_midi.PrettyMIDI object
    """

    assert len(midi_obj.instruments) == 1
    pedals = read_sustain_pedal(midi_obj)
    for pedal in pedals:
        instrument = midi_obj.instruments[0]
        for note in instrument.notes:
            if pedal.start < note.end <= pedal.end:
                note.end = pedal.end
    return midi_obj


def to_midi_zero(midi_path, midi_min=21, midi_max=108, save_midi=False, save_name=None):
    """Convert midi files to midi-0 format (1 track). set resolution = 1000, tempo=120.

    :param
        midi_path: path to .mid file
        midi_min: minimum midi number to convert. belows will be ignored.
        midi_max: maximum midi number to convert. highers will be ignored.
        save_midi: if true, save midi with name *.midi0.mid
        save_name: full path of save file. if given, save midi file with given name.
    :return:
        0-type pretty_midi.Pretty_Midi object.
    """

    if save_name is None:
        save_name = midi_path.replace('.mid', '_midi0.mid')

    midi = pretty_midi.PrettyMIDI(midi_path)
    midi_new = pretty_midi.PrettyMIDI(resolution=1000, initial_tempo=120)
    instrument = pretty_midi.Instrument(0)
    for instruments in midi.instruments:
        for midi_note in instruments.notes:
            note_pitch = midi_note.pitch
            if midi_min <= note_pitch <= midi_max:
                instrument.notes.append(midi_note)
            else:
                print('note with pitch : {:d} detected. Omitted because note not in [{:d}, {:d}]'
                      .format(note_pitch, midi_min, midi_max))
        for controls in instruments.control_changes:
            instrument.control_changes.append(controls)
    midi_new.instruments.append(instrument)
    midi_new.remove_invalid_notes()
    if save_midi:
        midi_new.write(save_name)
    return midi_new


def read_sustain_pedal(midi_obj, threshold=0):
    """Read sustain pedal in midi.

    :param
        midi_obj: pretty_midi.Pretty_Midi object.
        threshold: threshold of velocity to activate/deactivate pedal
    :return:
        list of SustainPedal objects
    """
    assert len(midi_obj.instruments) == 1
    instrument = midi_obj.instruments[0]

    pedals = []
    current_pedal = None
    for control in instrument.control_changes:
        # 64 is allocated for sustain pedal, but MAPS uses 127 as pedal
        if control.number in [64, 127]:
            if control.value > threshold:
                if isinstance(current_pedal, SustainPedal):
                    current_pedal.end = control.time
                    pedals.append(current_pedal)
                current_pedal = SustainPedal(control.time, None, control.value, control.number)
            elif control.value <= threshold:
                if isinstance(current_pedal, SustainPedal):
                    current_pedal.end = control.time
                    pedals.append(current_pedal)
                    current_pedal = None
                else:
                    warnings.warn('Sustain pedal offset detected without onset. Omitted')
    if isinstance(current_pedal, SustainPedal):
        warnings.warn('Last Sustain pedal detected without offset. Add offset at end')
        current_pedal.end = midi_obj.get_end_time()
        pedals.append(current_pedal)
    return pedals


def mid2piano_roll(midi_path, pedal=False, onset=False, midi_min=21, midi_max=108, clean_midi=True, fps=50.0):
    """Convert midi into piano-roll like array

    :param
        midi_path: midi path
        pedal: if True, elongate offset according to pedal
        onset: if True, mark only onset frame
        midi_min: minimum midi number to convert. belows will be ignored.
        midi_max: maximum midi number to convert. highers will be ignored.
        clean_midi: if True, clean up midi file before process.
        fps: frame rate per second. accept float values(ex: 36.6)
    :return:
        numpy array of piano roll, (midi_num, time_frames)
    """
    assert (pedal and onset) is not True, 'pedal + onset is not reasonable'

    if clean_midi:
        mid = to_midi_zero(midi_path, midi_min, midi_max)
    else:
        mid = pretty_midi.PrettyMIDI(midi_path)
    if pedal:
        mid = elongate_offset_by_pedal(mid)

    max_step = int(np.ceil(mid.get_end_time() * fps))
    dim = midi_max - midi_min + 1

    roll = np.zeros((max_step, dim))

    def time_to_frame(start, end):
        start_frame = int(start * fps)
        end_frame = int(end * fps)
        return start_frame, end_frame

    if onset:
        for note in mid.instruments[0].notes:
            start_time = note.start
            end_time = np.min([start_time + ONSET_DURATION, note.end])
            start_frame, end_frame = time_to_frame(start_time, end_time)
            roll[start_frame: end_frame, note.pitch - midi_min] = 1
    else:
        for note in mid.instruments[0].notes:
            start_time = note.start
            end_time = note.end
            start_frame, end_frame = time_to_frame(start_time, end_time)
            roll[start_frame: end_frame, note.pitch - midi_min] = 1

    return roll


def piano_roll2chroma_roll(piano_roll):
    """Convert piano roll into chroma roll
    # TODO: fixed indexing, according to midi_min
    :param
        piano_roll: numpy array of shape (midi_num, time_frames)
    :return:
        chroma roll, numpy array of shape (12, time_frames)

    """

    chroma_roll = np.zeros((piano_roll.shape[0], 12))  # (time, class)
    for n in range(piano_roll.shape[1]):
        chroma_roll[:, n % 12] += piano_roll[:, n]
    chroma_roll = (chroma_roll >= 1).astype(np.int)
    return chroma_roll


def mid2chroma_roll(midi_path, pedal=False, onset=False):
    piano_roll = mid2piano_roll(midi_path, pedal=pedal, onset=onset)
    chroma_roll = piano_roll2chroma_roll(piano_roll)
    return chroma_roll
