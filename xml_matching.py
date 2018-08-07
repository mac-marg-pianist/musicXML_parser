#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import csv
import math
import os
import midi_utils.midi_utils as midi_utils
import pretty_midi
from mxp import MusicXMLDocument
# import sys
# # sys.setdefaultencoding() does not exist, here!
# reload(sys)  # Reload does the trick!
# sys.setdefaultencoding('UTF8')


absolute_tempos_keywords = ['adagio', 'lento', 'andante', 'andantino', 'moderato', 'allegretto', 'allegro', 'vivace',
                            'presto', 'prestissimo', 'animato', 'maestoso', 'pesante', 'veloce', 'tempo i']
relative_tempos_keywords = ['acc', 'accel', 'rit', 'ritardando', 'accelerando', 'rall', 'rallentando', 'ritenuto',
                            'a tempo', 'stretto', 'slentando', 'meno mosso', 'più mosso', 'allargando']

tempos_keywords = absolute_tempos_keywords + relative_tempos_keywords

absolute_dynamics_keywords = ['dynamic', 'ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff', 'fp']
relative_dynamics_keywords = ['rel_dynamic', 'crescendo', 'diminuendo', 'cresc', 'dim', 'dimin' 'sotto voce',
                              'mezza voce', 'sf', 'fz', 'sfz', 'sffz', 'allargando']

dynamics_keywords = absolute_dynamics_keywords + relative_dynamics_keywords

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
    for note in xml_notes:
        match_threshold = 0.1
        if note.is_rest:
            candidates_list.append([])
            continue
        note_start = note.note_duration.time_position
        if note.note_duration.after_grace_note:
            note_start += 0.5
            match_threshold = 0.6
        # check grace note and adjust time_position
        note_pitch = note.pitch[1]
        temp_list = [{'index': index, 'midi_note': midi_note} for index, midi_note in enumerate(midi_notes) if abs(midi_note.start - note_start) < match_threshold and midi_note.pitch == note_pitch]
        candidates_list.append(temp_list)


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

def match_xml_midi_perform(xml_notes, midi_notes, perform_notes, corresp):
    xml_notes = apply_tied_notes(xml_notes)
    match_list = matchXMLtoMIDI(xml_notes, midi_notes)
    score_pairs = make_xml_midi_pair(xml_notes, midi_notes, match_list)
    xml_perform_match = match_score_pair2perform(score_pairs, perform_notes, corresp)
    perform_pairs = make_xml_midi_pair(xml_notes, perform_notes, xml_perform_match)

    return score_pairs, perform_pairs


def extract_notes(xml_Doc, melody_only = False):
    parts = xml_Doc.parts[0]
    notes =[]
    previous_grace_notes = []
    for measure in parts.measures:
        for note in measure.notes:
            if melody_only:
                if note.voice==1:
                    notes, previous_grace_notes= check_notes_and_append(note, notes, previous_grace_notes)
            else:
                notes, previous_grace_notes = check_notes_and_append(note, notes, previous_grace_notes)
    notes = apply_after_grace_note_to_chord_notes(notes)
    if melody_only:
        notes = delete_chord_notes_for_melody(notes)
    notes = apply_tied_notes(notes)
    notes.sort(key=lambda x: x.note_duration.xml_position)
    for note in notes:
        if note.note_duration.after_grace_note:
            print(note)
    return notes

def check_notes_and_append(note, notes, previous_grace_notes):
    if note.note_duration.is_grace_note:
        previous_grace_notes.append(note)
    if not note.is_rest and not note.note_duration.is_grace_note:
        if len(previous_grace_notes) > 0:
            temp_grc = []
            grace_order = 0
            for grc in previous_grace_notes:
                if grc.voice == note.voice:
                    note.note_duration.after_grace_note = True
                    grc.note_duration.grace_order = grace_order
                    grace_order += 1
                    # notes.append(grc)
                else:
                    temp_grc.append(grc)
            previous_grace_notes = temp_grc
        notes.append(note)

    return notes, previous_grace_notes

def apply_after_grace_note_to_chord_notes(notes):
    for note in notes:
        if note.note_duration.after_grace_note:
            onset= note.note_duration.xml_position
            voice = note.voice
            chords = find(lambda x: x.note_duration.xml_position == onset and x.voice == voice, notes)
            for chd in chords:
                chd.note_duration.after_grace_note = True
    return notes

def extract_measure_position(xml_Doc):
    parts = xml_Doc.parts[0]
    measure_positions = []

    for measure in parts.measures:
        measure_positions.append(measure.start_xml_position)

    return measure_positions

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
        if note.note_duration.is_grace_note:
            find_normal_note(notes, i)
            print(note.note_duration.time_position)


    return xml_Doc


def find_normal_note(notes, grace_index):
    grace_note = notes[grace_index]
    return notes



def extract_perform_features(xml_notes, pairs, measure_positions):
    print(len(xml_notes), len(pairs))
    features = []
    velocity_mean = calculate_mean_velocity(pairs)
    total_length_tuple = calculate_total_length(pairs)
    # print(total_length_tuple[0], total_length_tuple[1] )
    measure_seocnds = make_midi_measure_seconds(pairs, measure_positions)
    for i in range(len(xml_notes)):
        note_position = xml_notes[i].note_duration.xml_position
        measure_index = binaryIndex(measure_positions, note_position)
        if measure_index+1 <len(measure_positions):
            measure_length = measure_positions[measure_index+1] - measure_positions[measure_index]
            measure_sec_length = measure_seocnds[measure_index+1] - measure_seocnds[measure_index]
        else:
            measure_length = measure_positions[measure_index] - measure_positions[measure_index-1]
            measure_sec_length = measure_seocnds[measure_index] - measure_seocnds[measure_index-1]
        # length_tuple = (measure_length, measure_sec_length)
        feature ={}
        feature['pitch_interval'] = calculate_pitch_interval(xml_notes, i)
        feature['duration_ratio'] = calculate_duration_ratio(xml_notes, i)
        feature['beat_position'] = (note_position-measure_positions[measure_index]) / measure_length

        dynamic_words = dynamic_words_flatten(xml_notes[i])
        feature['dynamic'] = keyword_into_onehot(dynamic_words, dynamics_keywords)
        feature['tempo'] = keyword_into_onehot(xml_notes[i].tempo, tempos_keywords)

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
        if midi_ioi<=0 or xml_ioi<=0 or total_length[1] <= 0  or total_length[0] <=0:
            return None, None
        xml_length = pairs[index]['xml'].note_duration.duration
        midi_length = pairs[index]['midi'].end - pairs[index]['midi'].start
        ioi = math.log( midi_ioi/total_length[1]  /  (xml_ioi/total_length[0]), 10)

        articulation = xml_ioi/xml_length / (midi_ioi/midi_length)
    else:
        ioi = None
        articulation = None
    return ioi, articulation


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
        duration_ratio = math.log(xml_notes[index+1].note_duration.duration / xml_notes[index].note_duration.duration, 10)
    else:
        duration_ratio = None
    return duration_ratio


def load_entire_subfolder(path):
    entire_pairs = []
    midi_list = [os.path.join(dp, f) for dp, dn, filenames in os.walk(path) for f in filenames if
              f == 'midi.mid']
    for midifile in midi_list:
        foldername = os.path.split(midifile)[0] + '/'
        mxl_name = foldername + 'xml.mxl'
        xml_name = foldername + 'xml.xml'
        if os.path.isfile(mxl_name) and os.path.isfile(xml_name) :
            print(foldername)
            piece_pairs = load_pairs_from_folder(foldername)
            entire_pairs.append(piece_pairs)

    return entire_pairs

def load_pairs_from_folder(path):
    xml_name = path+'xml.xml'
    score_midi_name = path+'midi.mid'

    XMLDocument = MusicXMLDocument(xml_name)
    xml_notes = extract_notes(XMLDocument, melody_only=True)
    score_midi = midi_utils.to_midi_zero(score_midi_name)
    score_midi_notes = score_midi.instruments[0].notes
    match_list = matchXMLtoMIDI(xml_notes, score_midi_notes)
    score_pairs = make_xml_midi_pair(xml_notes, score_midi_notes, match_list)
    measure_positions = extract_measure_position(XMLDocument)
    filenames = os.listdir(path)
    perform_features_piece = []
    for file in filenames:
        if file[-18:] == '_infer_corresp.txt':
            perf_name = file.split('_infer')[0]
            perf_midi_name = path + perf_name + '.mid'
            perf_midi = midi_utils.to_midi_zero(perf_midi_name)
            #elongate offset
            perf_midi = midi_utils.elongate_offset_by_pedal(perf_midi)
            perf_midi_notes= perf_midi.instruments[0].notes
            corresp_name = path + file
            corresp = read_corresp(corresp_name)

            xml_perform_match = match_score_pair2perform(score_pairs, perf_midi_notes, corresp)
            perform_pairs = make_xml_midi_pair(xml_notes, perf_midi_notes, xml_perform_match)

            perform_features = extract_perform_features(xml_notes, perform_pairs, measure_positions)
            perform_features_piece.append(perform_features)

    return perform_features_piece


def make_midi_measure_seconds(pairs, measure_positions):
    xml_positions = []
    pair_indexes = []
    for i in range(len(pairs)):
        if not pairs[i] == []:
            xml_positions.append(pairs[i]['xml'].note_duration.xml_position)
            pair_indexes.append(i)
    # xml_positions = [pair['xml'].note_duration.xml_position for pair in pairs]
    measure_seconds = []
    for measure_start in measure_positions:
        pair_index = pair_indexes[binaryIndex(xml_positions, measure_start)]
        if pairs[pair_index]['xml'].note_duration.xml_position == measure_start:
            measure_seconds.append(pairs[pair_index]['midi'].start)
        else:
            left_second = pairs[pair_index]['midi'].start
            left_position = pairs[pair_index]['xml'].note_duration.xml_position
            while pair_index+1<len(pairs) and pairs[pair_index+1] == []:
                pair_index += 1
            if pair_index+1 == len(pairs):
                measure_seconds.append(max(measure_seconds[-1], left_second ))
                continue
            right_second = pairs[pair_index+1]['midi'].start
            right_position = pairs[pair_index+1]['xml'].note_duration.xml_position

            interpolated_second = left_second + (measure_start-left_position) / (right_position-left_position) * (right_second-left_second)
            measure_seconds.append(interpolated_second)
    return measure_seconds

def binaryIndex(alist, item):
    first = 0
    last = len(alist)-1
    midpoint = 0

    if(item< alist[first]):
        return 0

    while first<last:
        midpoint = (first + last)//2
        currentElement = alist[midpoint]

        if currentElement < item:
            if alist[midpoint+1] > item:
                return midpoint
            else: first = midpoint +1;
            if first == last and alist[last] > item:
                return midpoint
        elif currentElement > item:
            last = midpoint -1
        else:
            while alist[midpoint+1] == item:
                midpoint += 1
            return midpoint
    return last





def applyIOI(xml_notes, midi_notes, features, feature_list):
    IOIratio = feature_list[0]
    articulation = feature_list[1]
    loudness = feature_list[2]
    #len(features) always equal to len(xml_notes) by its definition
    xml_ioi_ratio_pairs = []
    ioi_index =0
    if not len(xml_notes) == len(IOIratio):
        for i in range(len(features)):
            if not features[i]['IOI_ratio'] == None:
                # [xml_position, time_position, ioi_ratio]
                temp_pair = {'xml_pos': xml_notes[i].note_duration.xml_position, 'midi_pos' : xml_notes[i].note_duration.time_position, 'ioi': IOIratio[ioi_index]}
                xml_ioi_ratio_pairs.append(temp_pair)
                ioi_index += 1
        if not ioi_index  == len(IOIratio):
            print('check ioi_index', ioi_index)
    else:
        for i in range(len(xml_notes)):
            note = xml_notes[i]
            temp_pair = {'xml_pos': note.note_duration.xml_position, 'midi_pos' : note.note_duration.time_position, 'ioi': IOIratio[i]}
            xml_ioi_ratio_pairs.append(temp_pair)
    # print(len(IOIratio), len(xml_ioi_ratio_pairs))

    default_tempo = xml_notes[0].state.qpm / 60 * xml_notes[0].state.divisions
    default_velocity = 64

    # in case the xml_position of first note is not 0
    current_sec = (xml_ioi_ratio_pairs[0]['xml_pos'] - 0) / default_tempo
    tempo_mapping_list = [ [xml_ioi_ratio_pairs[0]['midi_pos'] ] , [current_sec]]
    for i in range(len(xml_ioi_ratio_pairs)-1):
        pair = xml_ioi_ratio_pairs[i]
        next_pair = xml_ioi_ratio_pairs[i+1]
        note_length = next_pair['xml_pos'] - pair['xml_pos']
        tempo_ratio =  1/ (10 ** pair['ioi'])
        tempo = default_tempo * tempo_ratio
        note_length_second = note_length / tempo
        next_sec = current_sec + note_length_second
        current_sec = next_sec
        tempo_mapping_list[0].append( next_pair['midi_pos'] )
        tempo_mapping_list[1].append( current_sec )

    # print(tempo_mapping_list)
    print(len(tempo_mapping_list[0]), len(articulation))

    for note in midi_notes:
        note = make_new_note(note, tempo_mapping_list[0], tempo_mapping_list[1], articulation, loudness, default_velocity)
    return midi_notes

def make_new_note(note, time_a, time_b, articulation, loudness, default_velocity):
    index = binaryIndex(time_a, note.start)
    new_onset = cal_new_onset(note.start, time_a, time_b)
    temp_offset = cal_new_onset(note.end, time_a, time_b)
    new_duration = (temp_offset-new_onset) * articulation[index]
    new_offset = new_onset + new_duration
    new_velocity = min([max([int(default_velocity * (10 ** loudness[index])) , 0]), 127])

    note.start= new_onset
    note.end = new_offset
    note.velocity = new_velocity

    return note

def cal_new_onset(note_start, time_a, time_b):
    index = binaryIndex(time_a, note_start)
    time_org = time_a[index]
    new_time = interpolation(note_start, time_a, time_b, index)

    return new_time



def interpolation(a, list1, list2, index):
    if index == len(list1)-1:
        index += -1

    a1 = list1[index]
    b1 = list2[index]
    a2 = list1[index+1]
    b2 = list2[index+1]
    return b1+ (a-a1) / (a2-a1) * (b2 - b1)


def save_midi_notes_as_piano_midi(midi_notes, output_name):
    piano_midi = pretty_midi.PrettyMIDI()
    piano_program = pretty_midi.instrument_name_to_program('Acoustic Grand Piano')
    piano = pretty_midi.Instrument(program=piano_program)

    for note in midi_notes:
        piano.notes.append(note)
    piano_midi.instruments.append(piano)
    piano_midi.write(output_name)


def extract_directions(xml_doc):
    directions = []
    for part in xml_doc.parts:
        for measure in part.measures:
            for direction in measure.directions:
                directions.append(direction)

    directions.sort(key=lambda x: x.xml_position)
    cleaned_direction = []
    for i in range(len(directions)):
        dir = directions[i]
        if not dir.type == None:
            if dir.type['type'] == "none":
                for j in range(i):
                    prev_dir = directions[i-j]
                    prev_key = prev_dir.type['type']

                    if prev_key == "crescendo":
                        dir.type['type'] = 'crescendo'
                        break
                    elif prev_key == "diminuendo":
                        dir.type['type'] = 'diminuendo'
                        break
            cleaned_direction.append(dir)
        else:
            print(vars(dir.xml_direction))

    return cleaned_direction

def merge_start_end_of_direction(directions):
    for i in range(len(directions)):
        dir = directions[i]
        type_name = dir.type['type']
        if type_name in ['crescendo', 'diminuendo', 'pedal'] and dir.type['content'] == "stop":
            for j in range(i):
                prev_dir = directions[i-j]
                prev_type_name = prev_dir.type['type']
                if type_name == prev_type_name and prev_dir.type['content'] == "start" and dir.staff == prev_dir.staff:
                    prev_dir.end_xml_position = dir.xml_position
                    break
    dir_dummy = []
    for dir in directions:
        type_name = dir.type['type']
        if type_name in ['crescendo', 'diminuendo', 'pedal'] and dir.type['content'] != "stop":
            # directions.remove(dir)
            dir_dummy.append(dir)
        elif type_name == 'words':
            dir_dummy.append(dir)
    directions = dir_dummy
    return directions


def apply_directions_to_notes(xml_notes, directions):
    absolute_dynamics, relative_dynamics = get_dynamics(directions)
    absolute_dynamics_position = [dyn.xml_position for dyn in absolute_dynamics]
    # for dyn in absolute_dynamics:
    #     print(dyn)
    absolute_tempos = get_tempos(directions)
    absolute_tempos_position = [tmp.xml_position for tmp in absolute_tempos]

    for note in xml_notes:
        index = binaryIndex(absolute_dynamics_position, note.note_duration.xml_position)
        note.dynamic.absolute = absolute_dynamics[index].type['content']
        tempo_index = binaryIndex(absolute_tempos_position, note.note_duration.xml_position)
        # note.tempo.absolute = absolute_tempos[tempo_index].type[absolute_tempos[tempo_index].type.keys()[0]]
        note.tempo = absolute_tempos[tempo_index].type['content']

        # have to improve algorithm
        for rel in relative_dynamics:
            if note.note_duration.xml_position >= rel.xml_position and note.note_duration.xml_position <= rel.end_xml_position:
                note.dynamic.relative.append(rel)

    return xml_notes


def extract_directions_by_keywords(directions, keywords):
    sub_directions =[]

    for dir in directions:
        if dir.type['type'] in keywords:
            sub_directions.append(dir)
        elif dir.type['type'] == 'words':
            if dir.type['content'].replace(',', '').replace('.', '').lower() in keywords:
                sub_directions.append(dir)
            else:
                word_split = dir.type['content'].replace(',', ' ').replace('.', ' ').split(' ')
                for w in word_split:
                    if w.lower() in keywords:
                        # dir.type[keywords[0]] = dir.type.pop('words')
                        # dir.type[keywords[0]] = w
                        sub_directions.append(dir)

            # elif dir.type['words'].split('sempre ')[-1] in keywords:
            #     dir.type['dynamic'] = dir.type.pop('words')
            #     dir.type['dynamic'] = dir.type['dynamic'].split('sempre ')[-1]
            #     sub_directions.append(dir)
            # elif dir.type['words'].split('subito ')[-1] in keywords:
            #     dir.type['dynamic'] = dir.type.pop('words')
            #     dir.type['dynamic'] = dir.type['dynamic'].split('subito ')[-1]
            #     sub_directions.append(dir)

    return sub_directions


def get_dynamics(directions):
    absolute_dynamics = extract_directions_by_keywords(directions, absolute_dynamics_keywords)
    relative_dynamics = extract_directions_by_keywords(directions, relative_dynamics_keywords)
    abs_dynamic_dummy = []
    for abs in absolute_dynamics:
        if abs.type['content'] in ['sf', 'fz', 'sfz', 'sffz']:
            relative_dynamics.append(abs)
        else:
            abs_dynamic_dummy.append(abs)

    absolute_dynamics = abs_dynamic_dummy

    relative_dynamics.sort(key=lambda x:x.xml_position)
    relative_dynamics = merge_start_end_of_direction(relative_dynamics)
    absolute_dynamics_position = [dyn.xml_position for dyn in absolute_dynamics]
    relative_dynamics_position = [dyn.xml_position for dyn in relative_dynamics]

    for rel in relative_dynamics:
        index = binaryIndex(absolute_dynamics_position, rel.xml_position)
        rel.previous_dynamic = absolute_dynamics[index].type['content']
        if rel.type['type'] == 'dynamic': # sf, fz, sfz
            rel.end_xml_position = rel.xml_position
        if index+1 < len(absolute_dynamics):
            rel.next_dynamic = absolute_dynamics[index+1].type['content']
            if not hasattr(rel, 'end_xml_position'):
                rel.end_xml_position = absolute_dynamics_position[index+1]

    return absolute_dynamics, relative_dynamics


def get_tempos(directions):

    # print(tempos_keywords)
    absolute_tempos = extract_directions_by_keywords(directions, tempos_keywords)
    # relative_tempos = extract_directions_by_keywords(directions, relative_tempos_keywords)
    print(absolute_tempos)
    return absolute_tempos




def get_all_words_from_folders(path):
    entire_words = []
    xml_list = [os.path.join(dp, f) for dp, dn, filenames in os.walk(path) for f in filenames if
              f == 'xml.xml']

    for xmlfile in xml_list:
        xml_doc = MusicXMLDocument(xmlfile)
        directions = extract_directions(xml_doc)

        words = [dir for dir in directions if dir.type['type'] =='words']

        for wrd in words:
            entire_words.append(wrd.type['content'])

    entire_words = list(set(entire_words))
    return entire_words

def keyword_into_onehot(attribute, keywords):
    one_hot = [0] * len(keywords)
    if attribute in keywords:
        index = keywords.index(attribute)
        one_hot[index] = 1

    word_split = attribute.replace(',', ' ').replace('.', ' ').split(' ')
    for w in word_split:
        if w.decode('utf-8').lower() in keywords:
            index = keywords.index(w.decode('utf-8').lower())
            one_hot[index] = 1

    return one_hot


def dynamic_words_flatten(note):
    dynamic_words = note.dynamic.absolute
    if not note.dynamic.relative == []:
        for rel in note.dynamic.relative:
            dynamic_words = dynamic_words + ' ' + rel.type['content']

    return dynamic_words