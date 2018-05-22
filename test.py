from magenta import MusicXMLDocument
XMLDocument = MusicXMLDocument("magenta/testdata/flute_scale.xml")

midi_resolution = XMLDocument.midi_resolution
parts = XMLDocument.parts[0]
_score_parts = XMLDocument._score_parts
_state = XMLDocument._state
total_time_secs = XMLDocument.total_time_secs

# print(midi_resolution)
# print(parts)
# print(_score_parts)
# print('state;', _state)
# print(total_time_secs)

measure_1 = parts.measures[1].notes
#measure_1 = [[vars(x), vars(x.note_duration), vars(x.note_duration.state), vars(x.note_duration.state.time_signature)] for x in measure_1]
print([x.pitch for x in measure_1])
