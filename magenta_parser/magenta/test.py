import musicxml_parser

XMLDocument = musicxml_parser.MusicXMLDocument("testdata/flute_scale.xml")

midi_resolution = XMLDocument.midi_resolution
parts = XMLDocument.parts[0]
_score_parts = XMLDocument._score_parts
_state = XMLDocument._state
total_time_secs = XMLDocument.total_time_secs





print(midi_resolution)
print(parts)
print(_score_parts)
print('state;', _state)
print(total_time_secs)


measure_1 = parts.measures[0].notes

measure_1 = [[x.pitch, x.is_rest, vars(x.note_duration)] for x in measure_1]

print(measure_1)

# print(Part(parts[0]))


