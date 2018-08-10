#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mxp import MusicXMLDocument
import midi_utils.midi_utils as midi_utils
import xml_matching
import pickle

# folderDir = 'mxp/testdata/chopin10-3/'
# folderDir = 'chopin/Chopin_Polonaises/61/'
folderDir = 'chopin_cleaned/Chopin_Ballade/1/'
# folderDir = 'mxp/testdata/dummy/chopin_ballade3/'
# artistName = 'Sun08'
artistName = 'Ye01'
xmlname = 'musicxml_cleaned.musicxml'
# xmlname = 'xml.xml'
midiname= 'midi_cleaned.mid'

XMLDocument = MusicXMLDocument(folderDir + xmlname)
melody_notes = xml_matching.extract_notes(XMLDocument, melody_only=True)
melody_notes.sort(key=lambda x: x.note_duration.time_position)
score_midi = midi_utils.to_midi_zero(folderDir + midiname)
perform_midi = midi_utils.to_midi_zero(folderDir + artistName + '.mid')
perform_midi = midi_utils.elongate_offset_by_pedal(perform_midi)
score_midi_notes = score_midi.instruments[0].notes
perform_midi_notes = perform_midi.instruments[0].notes
corresp = xml_matching.read_corresp(folderDir + artistName + "_infer_corresp.txt")
score_pairs, perform_pairs = xml_matching.match_xml_midi_perform(melody_notes,score_midi_notes, perform_midi_notes, corresp)


# Check xml notes
# for i in range(len(melody_notes)-1):
#     # diff = (melody_notes[i+1].note_duration.time_position - melody_notes[i].note_duration.time_position) * 10000
#     # print(diff, melody_notes[i].note_duration.xml_position)
#     print(melody_notes[i].pitch, melody_notes[i].note_duration.xml_position,  melody_notes[i].note_duration.time_position)




#Check score_pairs
# non_matched_count = 0
# for pair in score_pairs:
#     if pair ==[]:
#         non_matched_count += 1
#         print (pair)
#     else:
#         print('XML Note pitch:', pair['xml'].pitch , ' and time: ', pair['xml'].note_duration.time_position , '-- MIDI: ', pair['midi'])
# print('Number of non matched XML notes: ', non_matched_count)

directions = xml_matching.extract_directions(XMLDocument)
for dir in directions:
    print(dir)
melody_notes = xml_matching.apply_directions_to_notes(melody_notes, directions)
# #
# for note in melody_notes:
#     # print(note.pitch, note.note_duration.xml_position, note.dynamic.absolute, note.tempo)
#     # print(note.pitch, note.note_duration.xml_position, note.dynamic.absolute, note.tempo.absolute, note.note_notations)
#     print(vars(note.note_notations))
#     if not note.dynamic.relative == []:
#         for rel in note.dynamic.relative:
#             print(rel)
#             print(rel.end_xml_position)

# for dir in directions:
#     # print(dir)
#     if not dir.type == None and dir.type.keys()[0] == 'words':
#         # print(dir)
#         pass

# words = xml_matching.get_all_words_from_folders('chopin/')
# for wrd in words:
#     print (wrd)


#
measure_positions = xml_matching.extract_measure_position(XMLDocument)
features = xml_matching.extract_perform_features(melody_notes, perform_pairs, measure_positions)

print(len(features[0]['dynamic']), len(features[0]['tempo']))
#
# ioi_list = []
# articul_list =[]
# loudness_list = []
# for feat in features:
#     if not feat['IOI_ratio'] == None:
#         ioi_list.append(feat['IOI_ratio'])
#         articul_list.append(feat['articulation'])
#         loudness_list.append(feat['loudness'])
#
# feature_list = [ioi_list, articul_list, loudness_list]
#
# ioi_list = [feat['IOI_ratio'] for feat in features ]
#
# new_midi = xml_matching.applyIOI(melody_notes, score_midi_notes, features, feature_list)
#
# for note in new_midi:
#     print(note)
#
# xml_matching.save_midi_notes_as_piano_midi(new_midi, 'my_first_midi.mid')


# load and save data
chopin_pairs = xml_matching.load_entire_subfolder('chopin_cleaned/')
# print(chopin_pairs)
with open("pairs_entire4.dat", "wb") as f:
    pickle.dump(chopin_pairs, f, protocol=2)
