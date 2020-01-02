def get_playable_notes(xml_part, melody_only=False):
    notes = []
    measure_number = 1
    for measure in xml_part.measures:
        for note in measure.notes:
            note.measure_number = measure_number
            notes.append(note)
        measure_number += 1

    notes, rests = classify_notes(notes, melody_only=melody_only)

    '''
    notes = self.apply_after_grace_note_to_chord_notes(notes)
    if melody_only:
        notes = self.delete_chord_notes_for_melody(notes)
    notes = self.apply_tied_notes(notes)
    notes.sort(key=lambda x: (x.note_duration.xml_position,
                x.note_duration.grace_order, -x.pitch[1]))
    notes = self.check_overlapped_notes(notes)
    notes = self.apply_rest_to_note(notes, rests)
    notes = self.omit_trill_notes(notes)
    notes = self.extract_and_apply_slurs(notes)
    # notes = self.rearrange_chord_index(notes)
    '''
    return notes


def classify_notes(notes, melody_only=False):
    # classify notes into notes, grace_notes, and rests.
    grace_tmp = []
    rests = []
    for note in notes:
        if melody_only:
            if note.voice != 1:
                continue
        if note.note_duration.is_grace_note:
            grace_tmp.append(note)
            notes.append(note)
        elif not note.is_rest:
            if len(grace_tmp) > 0:
                rest_grc = []
                added_grc = []
                grace_order = -1
                for grc in reversed(grace_tmp):
                    if grc.voice == note.voice:
                        note.note_duration.preceded_by_grace_note = True
                        grc.note_duration.grace_order = grace_order
                        grc.following_note = note
                        if grc.chord_index == 0:
                            grace_order -= 1
                        added_grc.append(grc)
                    else:
                        rest_grc.append(grc)
                num_added = abs(grace_order) - 1
                for grc in added_grc:
                    # grc.note_duration.grace_order /= num_added
                    grc.note_duration.num_grace = num_added
                if abs(grc.note_duration.grace_order) == num_added:
                    grc.note_duration.is_first_grace_note = True
                grace_tmp = rest_grc
                notes.append(note)
            else:
                assert note.is_rest
                if note.is_print_object:
                    rests.append(note)

    return notes, rests