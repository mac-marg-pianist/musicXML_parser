from magenta import MusicXMLDocument
import midi_utils.midi_utils as midi_utils
import xml_matching


XMLDocument = MusicXMLDocument("magenta/testdata/chopin10-3/xml.xml")
melody_notes = xml_matching.extract_notes(XMLDocument, melody_only=True)
# midi = pretty_midi.PrettyMIDI("magenta/testdata/chopin10-3/midi.mid")
score_midi = midi_utils.to_midi_zero("magenta/testdata/chopin10-3/midi.mid")
perform_midi = midi_utils.to_midi_zero("magenta/testdata/chopin10-3/Sun08.mid")
score_midi_notes = score_midi.instruments[0].notes
perform_midi_notes = perform_midi.instruments[0].notes
corresp = xml_matching.read_corresp("magenta/testdata/chopin10-3/Sun08_infer_corresp.txt")


score_pairs, perform_pairs = xml_matching.match_xml_midi_perfrom(melody_notes,score_midi_notes, perform_midi_notes, corresp)


#
#
# for pair in pairs:
#     print('XML: ', pair['xml'].pitch, pair['xml'].note_duration.time_position, 'MIDI: ', pair['midi'])
#
non_matched_count = 0
for pair in score_pairs:
    print(pair)
    if pair ==[]:
        non_matched_count += 1

print(len(score_pairs), non_matched_count)
melody_notes.sort(key=lambda x: x.note_duration.time_position)
for note in melody_notes:
    # print(note.note_duration.time_position, note.note_duration.xml_position)
    pass
#

# for i in range(len(melody_notes)-1):
#     diff = (melody_notes[i+1].note_duration.time_position - melody_notes[i].note_duration.time_position) * 10000
#     print(diff, melody_notes[i].note_duration.xml_position)

# tempo_list = XMLDocument.get_tempos()
# tempo_list = XMLDocument.recalculate_time_position()
# for tempo in tempo_list:
#     print(tempo, tempo.xml_position, tempo.new_time_position)

