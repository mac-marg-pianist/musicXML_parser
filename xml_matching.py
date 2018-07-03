from __future__ import division
import csv
import math

def apply_tied_notes(xml_parsed_notes):
    tie_clean_list = []
    for i in range(len(xml_parsed_notes)):
        if xml_parsed_notes[i].note_notations.tied_stop == False:
            tie_clean_list.append(xml_parsed_notes[i])
        else:
            for j in reversed(range(len(tie_clean_list))):
                if tie_clean_list[j].note_notations.tied_start == True and tie_clean_list[j].pitch[1] == xml_parsed_notes[i].pitch[1]:
                    tie_clean_list[j].note_duration.seconds +=  xml_parsed_notes[i].note_duration.seconds
                    tie_clean_list[j].note_duration.duration +=  xml_parsed_notes[i].note_duration.duration
                    tie_clean_list[j].note_duration.midi_ticks +=  xml_parsed_notes[i].note_duration.midi_ticks
                    break
    return tie_clean_list


def matchXMLtoMIDI(xml_notes, midi_notes):
    candidates_list = []
    match_list = []

    # for each note in xml, make candidates of the matching midi note
    for i in range(len(xml_notes)):
        note = xml_notes[i]
        if note.is_rest:
            candidates_list.append([])
            continue
        note_start = note.note_duration.time_position
        # check grace note and adjust time_position
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

def match_xml_midi_perfrom(xml_notes, midi_notes, perform_notes, corresp):
    xml_notes = apply_tied_notes(xml_notes)
    # print(len(xml_notes))
    match_list = matchXMLtoMIDI(xml_notes, midi_notes)
    score_pairs = make_xml_midi_pair(xml_notes, midi_notes, match_list)
    xml_perform_match = match_score_pair2perform(score_pairs, perform_notes, corresp)
    perform_pairs = make_xml_midi_pair(xml_notes, perform_notes, xml_perform_match)

    return score_pairs, perform_pairs


def extract_notes(xml_Doc, melody_only = False):
    parts = xml_Doc.parts[0]
    notes =[]
    for measure in parts.measures:
        for note in measure.notes:
            if not note.is_rest and not note.note_duration.is_grace_note:
                if melody_only:
                    if note.voice ==1:
                        notes.append(note)
                else:
                    notes.append(note)
    if melody_only:
        notes = delete_chord_notes_for_melody(notes)

    notes = apply_tied_notes(notes)
    return notes

def delete_chord_notes_for_melody(melody_notes):
    note_onset_positions = list(set(note.note_duration.xml_position for note in melody_notes))
    note_onset_positions.sort()
    unique_melody = []
    for onset in note_onset_positions:
        notes = find(lambda x: x.note_duration.xml_position == onset, melody_notes)
        if len(notes) == 1:
            unique_melody.append(notes[0])
        else:
            notes.sort(key=lambda x: x.pitch[1])
            unique_melody.append(notes[-1])

    return unique_melody

def find(f, seq):
  """Return first item in sequence where f(item) == True."""
  items_list = []
  for item in seq:
    if f(item):
      items_list.append(item)
  return items_list


def apply_grace(xml_Doc):
    notes = extract_notes(xml_Doc)
    for i in range(len(notes)):
        note = notes[i]
        if note.is_grace_note:
            pass
    return xml_Doc


def find_normal_note(notes, grace_index):
    grace_note = notes[grace_index]
    return notes



def extract_perform_features(xml_notes, pairs):
    print(len(xml_notes), len(pairs))
    features = []
    velocity_mean = calculate_mean_velocity(pairs)
    total_length_tuple = calculate_total_length(pairs)
    print(total_length_tuple[0], total_length_tuple[1] )

    for i in range(len(xml_notes)):
        feature ={}
        feature['pitch_interval'] = calculate_pitch_interval(xml_notes, i)
        feature['duration_ratio'] = calculate_duration_ratio(xml_notes, i)
        if not pairs[i] == []:
            feature['IOI_ratio'], feature['articulation']  = calculate_IOI_articulation(pairs,i, total_length_tuple)
            feature['loudness'] = math.log( pairs[i]['midi'].velocity / velocity_mean, 10)
        else:
            feature['IOI_ratio'] = None
            feature['articulation'] = None
            feature['loudness'] = 0
        # feature['articulation']
        features.append(feature)

    return features

def calculate_IOI_articulation(pairs, index, total_length):
    if index < len(pairs)-1 and not pairs[index+1] == [] :
        xml_ioi = pairs[index+1]['xml'].note_duration.xml_position - pairs[index]['xml'].note_duration.xml_position
        midi_ioi =  pairs[index+1]['midi'].start - pairs[index]['midi'].start
        xml_length = pairs[index]['xml'].note_duration.duration
        midi_length = pairs[index]['midi'].end - pairs[index]['midi'].start

        ioi = math.log( midi_ioi/total_length[1]  /  (xml_ioi/total_length[0]), 10)

        articulation = xml_ioi/xml_length / (midi_ioi/midi_length)
    else:
        ioi = None
        articulation = None
    return ioi, articulation

def calcuate_articluation(pairs, index, ioi):


    return

def calculate_total_length(pairs):
    for i in range(len(pairs)):
        if not pairs[-i-1] == []:
            xml_length =  pairs[-i-1]['xml'].note_duration.xml_position - pairs[0]['xml'].note_duration.xml_position
            midi_length = pairs[-i-1]['midi'].start - pairs[0]['midi'].start
            return (xml_length, midi_length)

def calculate_mean_velocity(pairs):
    sum = 0
    length =0
    for pair in pairs:
        if not pair == []:
            sum += pair['midi'].velocity
            length += 1

    return sum/float(length)

def calculate_pitch_interval(xml_notes, index):
    if index < len(xml_notes)-1:
        pitch_interval = xml_notes[index+1].pitch[1] - xml_notes[index].pitch[1]
    else:
        pitch_interval = None
    return pitch_interval

def calculate_duration_ratio(xml_notes, index):
    if index < len(xml_notes)-1:
        duration_ratio = math.log(xml_notes[index+1].note_duration.duration / float(xml_notes[index].note_duration.duration), 10)
    else:
        duration_ratio = None
    return duration_ratio