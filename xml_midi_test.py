from mxp import MusicXMLDocument
import midi_utils.midi_utils as midi_utils
import xml_matching


XMLDocument = MusicXMLDocument("mxp/testdata/chopin10-3/xml.xml")
melody_notes = xml_matching.extract_notes(XMLDocument, melody_only=False)
melody_notes.sort(key=lambda x: x.note_duration.time_position)
score_midi = midi_utils.to_midi_zero("mxp/testdata/chopin10-3/midi.mid")
perform_midi = midi_utils.to_midi_zero("mxp/testdata/chopin10-3/Sun08.mid")
score_midi_notes = score_midi.instruments[0].notes
perform_midi_notes = perform_midi.instruments[0].notes
corresp = xml_matching.read_corresp("mxp/testdata/chopin10-3/Sun08_infer_corresp.txt")


score_pairs, perform_pairs = xml_matching.match_xml_midi_perfrom(melody_notes,score_midi_notes, perform_midi_notes, corresp)


# Check xml notes
for i in range(len(melody_notes)-1):
    # diff = (melody_notes[i+1].note_duration.time_position - melody_notes[i].note_duration.time_position) * 10000
    # print(diff, melody_notes[i].note_duration.xml_position)
    print(melody_notes[i].pitch, melody_notes[i].note_duration.xml_position,  melody_notes[i].note_duration.time_position)




#Check score_pairs
# non_matched_count = 0
# for pair in score_pairs:
#     if pair ==[]:
#         non_matched_count += 1
#         print (pair)
#     else:
#         print('XML Note pitch:', pair['xml'].pitch , ' and time: ', pair['xml'].note_duration.time_position , '-- MIDI: ', pair['midi'])
# print('Number of non matched XML notes: ', non_matched_count)




# features = xml_matching.extract_perform_features(melody_notes, perform_pairs)
#
# for feature in features:
#     print(feature)
