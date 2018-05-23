from magenta import MusicXMLDocument
import pretty_midi
import midi_utils.midi_utils as midi_utils
import csv


XMLDocument = MusicXMLDocument("magenta/testdata/chopin10-3/xml.xml")
# midi = pretty_midi.PrettyMIDI("magenta/testdata/chopin10-3/midi.mid")
midi_cleaned = midi_utils.to_midi_zero("magenta/testdata/chopin10-3/midi.mid")
perform_midi = midi_utils.to_midi_zero("magenta/testdata/chopin10-3/Sun08.mid")
perform_midi_notes = perform_midi.instruments[0].notes


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
print(midi_cleaned.__dict__.keys())
print(midi_cleaned.instruments[0].notes[0])

measure_1 = parts.measures[7].notes

# measure_1 = [[x.pitch, x.is_rest, vars(x.note_duration)] for x in measure_1]
measure_1 = [x.is_grace_note for x in measure_1]

# print(measure_1)
melody_notes= []

# print(parts.measures.__attr__)

for i in range(len(parts.measures)):
    for j in range(len(parts.measures[i].notes)):
        print(parts.measures[i].notes[j].is_grace_note)
        # pass


print(len(parts.measures))

for measures in parts.measures:
    for notes in measures.notes:
        if notes.voice ==1:
            if not notes.is_rest:
                melody_notes.append(notes)

for i in range(len(melody_notes)):
    # print(melody_notes[i].tied)
    pass

for notes in melody_notes:
    # print(vars(notes.note_duration))
    # print(notes.note_duration.time_position)
    if notes.is_rest == False:
        if notes.note_duration.time_position == 0:
            pass
            # print([vars(notes), vars(notes.note_duration)])
# # print(measure_1)

# for note in midi_cleaned.instruments[0].notes:
    # print(note)


# print(XMLDocument.parts[0])


print(len(melody_notes))
print(len(midi_cleaned.instruments[0].notes))





# print(melody_notes[5])
#
# for i in range(len(midi_cleaned.instruments[0].notes)):
#     print(midi_cleaned.instruments[0].notes[i])
# #
#
# for i in range(len(melody_notes)):
#     print(melody_notes[i])



def apply_tied_notes(xml_parsed_notes):
    tie_clean_list = []
    for i in range(len(xml_parsed_notes)):
        if xml_parsed_notes[i].tie == False or xml_parsed_notes[i].tie == 'start':
            tie_clean_list.append(xml_parsed_notes[i])
        elif xml_parsed_notes[i].tie == 'stop' or xml_parsed_notes[i].tie == 'start_stop':
            for j in reversed(range(len(tie_clean_list))):
                if tie_clean_list[j].tie == 'start' and tie_clean_list[j].pitch[1] == xml_parsed_notes[i].pitch[1]:
                    tie_clean_list[j].note_duration.seconds +=  xml_parsed_notes[i].note_duration.seconds
                    tie_clean_list[j].note_duration.duration +=  xml_parsed_notes[i].note_duration.duration
                    tie_clean_list[j].note_duration.midi_ticks +=  xml_parsed_notes[i].note_duration.midi_ticks
                    break
    return tie_clean_list


clean_melody = apply_tied_notes(melody_notes)
for i in range(len(clean_melody)):
    # print(clean_melody[i])
    # print(melody_notes[i])
    pass

def matchXMLtoMIDI(xml_notes, midi_notes):
    candidates_list = []
    match_list = []
    for i in range(len(xml_notes)):
        note = xml_notes[i]
        if note.is_rest:
            candidates_list.append([])
            continue
        note_start = note.note_duration.time_position
        if note.note_duration.time_position == 0 and note.note_duration.duration == 0:
            # print(i)
            note_start = xml_notes[i+1].note_duration.time_position
        note_pitch = note.pitch[1]
        temp_list = [{'index': index, 'midi_note': midi_note} for index, midi_note in enumerate(midi_notes) if abs(midi_note.start - note_start) < 0.1 and midi_note.pitch == note_pitch]
        candidates_list.append(temp_list)
        # print(temp_list)
        # print(note_start)

    for candidates in candidates_list:
        if len(candidates) ==1:
            matched_index = candidates[0]['index']
            match_list.append(matched_index)
        elif len(candidates) > 1:
            added = False
            for cand in candidates:
                if cand['index'] not in match_list:
                    match_list.append(cand['index'])
                    added = True
                    break
            if not added:
                match_list.append([])
        else:
            match_list.append([])
    return match_list

def make_xml_midi_pair(xml_notes, midi_notes, match_list):
    pairs = []
    for i in range(len(match_list)):
        if not match_list[i] ==[]:
            temp_pair = {'xml': xml_notes[i], 'midi': midi_notes[match_list[i]]}
            pairs.append(temp_pair)
        else:
            pairs.append([])
    return pairs


def read_corresp(txtpath):
    file = open(txtpath, 'r')
    reader = csv.reader(file, dialect='excel', delimiter='\t')
    corresp_list = []
    for row in reader:
        if len(row) == 1:
            continue
        temp_dic = {'alignID': row[0], 'alignOntime': row[1], 'alignSitch': row[2], 'alignPitch': row[3], 'alignOnvel': row[4], 'refID':row[5], 'refOntime':row[6], 'refSitch':row[7], 'refPitch':row[8], 'refOnvel':row[9] }
        corresp_list.append(temp_dic)

    return corresp_list


def find_by_key(list, key1, value1, key2, value2):
    for i, dic in enumerate(list):
        if abs(float(dic[key1]) - value1) <0.001 and int(dic[key2]) ==value2 :
            return i
    return -1

def find_by_attr(list, value1, value2):
    for i, obj in enumerate(list):
        if abs(obj.start - value1) <0.001 and obj.pitch ==value2 :
            return i
    return []




def match_score_pair2perform(pairs, perform_midi, corresp_list):
    match_list = []
    for pair in pairs:
        if pair == []:
            match_list.append([])
            continue
        ref_midi = pair['midi']
        index_in_coressp = find_by_key(corresp_list, 'refOntime', ref_midi.start, 'refPitch', ref_midi.pitch)
        corresp_pair = corresp_list[index_in_coressp]
        index_in_perform_midi = find_by_attr(perform_midi, float(corresp_pair['alignOntime']),  int(corresp_pair['alignPitch']))
        match_list.append(index_in_perform_midi)
    return match_list




    # print(clean_melody[-1])

corresp_list= read_corresp('magenta/testdata/chopin10-3/Sun08_infer_corresp.txt')
# print(corresp_list)



match_list = matchXMLtoMIDI(clean_melody, midi_cleaned.instruments[0].notes)
# print(match_list)

for i in range(len(match_list)):
    if match_list[i] == []:
        print([i, clean_melody[i]])
        # pass
    # print(clean_melody[i].is_grace_note)
    pass



pairs = make_xml_midi_pair(clean_melody, midi_cleaned.instruments[0].notes, match_list)

xml_perform_match = match_score_pair2perform(pairs, perform_midi_notes, corresp_list)
print(xml_perform_match)
perform_pairs =  make_xml_midi_pair(clean_melody, perform_midi_notes, xml_perform_match)


print(corresp_list[0]['refPitch'])
print(corresp_list[1]['refOntime'])


print(len(pairs))
#
#
# for pair in pairs:
#     print('XML: ', pair['xml'].pitch, pair['xml'].note_duration.time_position, 'MIDI: ', pair['midi'])
#
for pair in perform_pairs:
    if not pair ==[]:
        print('XML: ', pair['xml'].pitch, pair['xml'].note_duration.time_position, 'MIDI: ', pair['midi'])