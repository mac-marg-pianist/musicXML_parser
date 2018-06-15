# Updated 2018.06.01

import itertools
from operator import itemgetter
from magenta import MusicXMLDocument
from itertools import chain

class OnsetState(object):
  def __init__(self):
    self.current_onset = None
    self.previous_onset = None
    self.previous_wedge = None
    self.current_wedge = None

  def update_current_onset(self, onset):
    self.current_onset = onset

  def update_previous_onset(self, onset):
    self.previous_onset = onset

  def update_previous_wedge(self, wedge):
    self.previous_wedge = wedge
 
  def update_current_wedge(self, onset):
    self.current_wedge = onset

class Onset(OnsetState):
  def __init__(self, notes, previous_notes, on_set_position, on_set_total_num):
    OnsetState.__init__(self)
    self.notes = notes
    self.previous_notes = previous_notes
    self.on_set_position = on_set_position
    self.on_set_total_num = on_set_total_num
    self.accent = None            #[0] or [1]
    self.dynamic = None      # ('string', binary [0])
    self.crescendo = None        # ([0, 0, 0] ['start', 'stop', 'continue'] )
    self.diminuendo = None        # ([0, 0, 0] ['start', 'stop', 'continue'] )
    self.staccato = None     # ('string', binary [0])
    self.beat = None  # [0, 0, 0] [start_beat, middle_beat, last_beat] # 0 or 1
    self.execute()

  def execute(self):
    self._set_accent()
    self._set_beat()
    self._set_dynamic()
    self._set_wedge()
    self._set_staccato()
    self._set_pedal()

  def _set_accent(self):
    accent = [x.note_notations.is_accent for x in self.notes][0]
    vector = self._change_bool_to_vector('accent', accent)
    self.accent = vector

  def _set_beat(self):
    # start point of a measure
    if self.on_set_position == 1:
      self.beat = [0, 0, 0]
    # middle point of a measure
    if self.on_set_position == self.on_set_total_num:
      self.beat = [0, 1, 0]
    # end point of a measure
    else:
      self.beat = [0, 0, 1]

  def _set_dynamic(self):
    """
      check dynamic type and return binary
      vector = [0, 0] # vector[0] points 'p' dynamic group.
                      # vector[1] points 'f' dynamic group.
      Args:
        dynamic_type: p or f dynamic
    """
    dynamic_type = [x.direction.dynamic for x in self.notes][0]

    p_group = ['ppp', 'pp', 'p', 'mp']
    f_group = ['mf', 'f', 'ff', 'fff']

    if dynamic_type in p_group:
      vector = [0, 1]
    elif dynamic_type in f_group:
      vector = [1, 0]
    else:
      vector = [0, 0]
    self.dynamic = (dynamic_type, vector)

  def _set_wedge(self):
    """
      check wedge type and return binary
    """
    if self.previous_notes is not None:
      current_wedge = self._map_to_wedge(self.notes)
      previous_wedge = self.previous_wedge
     
      if self.previous_wedge is None:
        previous_wedge = self._map_to_wedge(self.previous_notes)
        self.previous_wedge = previous_wedge

      wedge_type = ['crescendo', 'diminuendo']
      result = []

      for type in wedge_type:
        current_wedge_val = list(current_wedge[type].values())
        previous_wedge_val = list(previous_wedge[type].values())
      # 이전에 continue이지만 값이 빠져있는 경우
      #   if previous_wedge_val[2] == 1 and current_wedge_val[2] == 0:
      #     current_wedge_val[0] = 1
      #     current_wedge_val[2] = 1
        
      # # # 이전에 start 이지만 continue 값이 빠져있는 경우
      #   if previous_wedge_val[1] == 1 and current_wedge_val[2] == 0:
      #     current_wedge_val[0] = 1
      #     current_wedge_val[2] = 1
        result.append(current_wedge_val)

      self.crescendo = result[0]
      self.diminuendo = result[1]
      print(result)


  def _map_to_wedge(self, notes):
    wedge = {'crescendo': {'on': 0, 'start': 0, 'continue': 0, 'stop': 0},
      'diminuendo': {'on': 0, 'start': 0, 'continue': 0, 'stop': 0}}

    all_wedge = [(x.direction.wedge_type, x.direction.wedge_status) for x in notes]
    #print(all_wedge)

    is_crescendo = 'crescendo' in chain(*all_wedge)
    is_diminuendo = 'diminuendo' in chain(*all_wedge)
    
    if is_crescendo:
      wedge['crescendo']['on'] = 1
      is_start = 'start' in chain(*all_wedge)
      is_stop = 'stop' in chain(*all_wedge)
      is_continue = 'continue' in chain(*all_wedge)

      wedge['crescendo']['start'] = 1 if is_start == True else 0
      wedge['crescendo']['stop'] = 1 if is_stop == True else 0
      wedge['crescendo']['continue'] = 1 if is_continue == True else 0

    if is_diminuendo:
      wedge['diminuendo']['on'] = 1
      is_start = 'start' in chain(*all_wedge)
      is_stop = 'stop' in chain(*all_wedge)
      is_continue = 'continue' in chain(*all_wedge)

      wedge['diminuendo']['start'] = 1 if is_start == True else 0
      wedge['diminuendo']['stop'] = 1 if is_stop == True else 0
      wedge['diminuendo']['continue'] = 1 if is_continue == True else 0
    
    #print(wedge.values())
    return wedge

    
  def _set_staccato(self):
    staccato = [x.note_notations.is_staccato for x in self.notes][0]
    vector = self._change_bool_to_vector('staccato', staccato)
    self.staccato = vector

  def _set_pedal(self):
    # 역시 같은 문제
    pass

  def _change_bool_to_vector(self, property_name, bool_type: bool):
    return (bool_type, [1]) if bool_type == True else (bool_type, [0])

class Main(OnsetState):
  def __init__(self):
    OnsetState.__init__(self)    
    self.readXML()

  def readXML(self):
    XMLDocument = MusicXMLDocument("xml.xml")
    parts = XMLDocument.parts[0]
    measure_num = len(parts.measures)
    for i in range(measure_num):
      
      # Read all notes in a measure
      measure =  parts.measures[i]
      notes = measure.notes
      # Sort notes by time position
      #sorted_notes = sorted(notes, key=lambda note: note.note_duration.time_position)

      print(">>> Measure", i+1)
      print([vars(x) for x in notes])
      # note_on_set_group = {k:[v for v in sorted_notes if v.note_duration.time_position == k] 
      #                       for k, val in itertools.groupby(sorted_notes, lambda x: x.note_duration.time_position)}
      
      # #print(note_on_set_group)
      # keyList=sorted(note_on_set_group.keys())
      # total = len(keyList)

      # for index, (key, group) in enumerate(note_on_set_group.items()):
      #   if index > 0:
      #     previous_onset = note_on_set_group[keyList[index-1]]
      #     position = index+1
      #     on_set = Onset(group, previous_onset, index+1, total)
      #   else:
      #     previous_onset = self.previous_onset
      #     on_set = Onset(group, previous_onset, index+1, total)

Main().readXML()





