from mxp import MusicXMLDocument
import midi_utils.midi_utils as midi_utils
import xml_matching
import matplotlib
import numpy as np
import pylab as pl

XMLDocument = MusicXMLDocument("mxp/testdata/chopin10-3/xml.xml")
melody_notes = xml_matching.extract_notes(XMLDocument, melody_only=True)
melody_notes.sort(key=lambda x: x.note_duration.time_position)
score_midi = midi_utils.to_midi_zero("mxp/testdata/chopin10-3/midi.mid")
perform_midi = midi_utils.to_midi_zero("mxp/testdata/chopin10-3/Sun08.mid")
score_midi_notes = score_midi.instruments[0].notes
perform_midi_notes = perform_midi.instruments[0].notes
corresp = xml_matching.read_corresp("mxp/testdata/chopin10-3/Sun08_infer_corresp.txt")


score_pairs, perform_pairs = xml_matching.match_xml_midi_perfrom(melody_notes,score_midi_notes, perform_midi_notes, corresp)


features = xml_matching.extract_perform_features(melody_notes, perform_pairs)
loudness =[]

for feature in features:
    loudness.append(feature['loudness'])
# print(loudness)
x = np.random.normal(size=100)

pl.hist(loudness,normed=True)
pl.show()