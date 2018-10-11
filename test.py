from mxp import MusicXMLDocument

XML_PATH = "mxp/testdata/chopin10-3/xml.xml"

XMLDocument = MusicXMLDocument(XML_PATH)

midi_resolution = XMLDocument.midi_resolution
parts = XMLDocument.parts[0]
_score_parts = XMLDocument._score_parts
_state = XMLDocument._state
total_time_secs = XMLDocument.total_time_secs

for i in range(len(parts.measures)):
  print("<=== Measure ===>", i)
  current = parts.measures[i].notes
  print([vars(x) for x in current])
  print(len([x.pitch for x in current]))