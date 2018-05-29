# Updated 2018.05.29

import itertools
from operator import itemgetter
from magenta import MusicXMLDocument
from itertools import chain

class OnsetState(object):
  def __init__(self):
    self.state = None

class Onset(object):
  
  def __init__(self, notes, previous_notes, on_set_position, on_set_total_num):
    self.notes = notes   
    self.previous_notes = previous_notes    
    self.on_set_position = on_set_position
    self.on_set_total_num = on_set_total_num
    self.accent = None
    self.dynamic = None      # ('string', binary [0])
    self.crescendo = None        # ([0, 0, 0] ['start', 'stop', 'continue'] )
    self.diminuendo = None        # ([0, 0, 0] ['start', 'stop', 'continue'] )

    self.staccato = None     # ('string', binary [0])
    self.beat = None         # [0, 0, 0] [start_beat, middle_beat, last_beat] # 0 or 1
    self.state = OnsetState()
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
    wedge = {'crescendo': {'on': 0, 'start': 0, 'continue': 0, 'stop': 0},
    'diminuendo': {'on': 0, 'start': 0, 'continue': 0, 'stop': 0}

    }

    current_wedge = [(x.direction.wedge_type, x.direction.wedge_status) for x in self.notes]
    # [('crescendo', 'stop'), ....]

    if self.previous_notes:
      # 아무런 정보가 없을 때 이전 wedge에서 가져온다. 
      if current_wedge[0][0] == None:
        previous_wedge = [(x.direction.wedge_type, x.direction.wedge_status) for x in self.previous_notes]
      
        is_stop_in_wedge = 'stop' in chain(*previous_wedge)

        # stop이 아닐 경우 이전 온셋 타임의 정보를 가져온다.
        if not(is_stop_in_wedge) and previous_wedge[0][0] != None:
          current_wedge = previous_wedge
          self.state.state = previous_wedge

        # !해결 필요한 곳
        # previous_wedge와 current_wedge가 모두 "None"일 경우
        # stop이 아닐 경우 이전 온셋 타임의 정보를 가져오지 않지만 업데이트되지 않음

        #print("--PREV---", previous_wedge)
        #print("--CURRENT---",  current_wedge)

    # 이 부분은 함수로 만들어야 됨 :: 리팩토링 필요.
    is_crescendo = 'crescendo' in chain(*current_wedge)
    is_diminuendo = 'diminuendo' in chain(*current_wedge)
    
    if is_crescendo:
      wedge['crescendo']['on'] = 1
      is_start = 'start' in chain(*current_wedge)
      is_stop = 'stop' in chain(*current_wedge)
      is_continue = 'continue' in chain(*current_wedge)

      wedge['crescendo']['start'] = 1 if is_start == True else 0
      wedge['crescendo']['stop'] = 1 if is_stop == True else 0
      wedge['crescendo']['continue'] = 1 if is_continue == True else 0

    if is_diminuendo:
      wedge['diminuendo']['on'] = 1
      is_start = 'start' in chain(*current_wedge)
      is_stop = 'stop' in chain(*current_wedge)
      is_continue = 'continue' in chain(*current_wedge)

      wedge['diminuendo']['start'] = 1 if is_start == True else 0
      wedge['diminuendo']['stop'] = 1 if is_stop == True else 0
      wedge['diminuendo']['continue'] = 1 if is_continue == True else 0
    
    # self => 저장

    
  def _set_staccato(self):
    staccato = [x.note_notations.is_staccato for x in self.notes][0]
    vector = self._change_bool_to_vector('staccato', staccato)
    self.staccato = vector

  def _set_pedal(self):
    # 역시 같은 문제

    pass

  def _change_bool_to_vector(self, property_name, bool_type: bool):
    return (bool_type, [1]) if bool_type == True else (bool_type, [0])
 
class Main(object):
  def __init__(self):
    self.previous_onset = None

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
      sorted_notes = sorted(notes, key=lambda note: note.note_duration.time_position)
      # Make note group list by time position 
      note_on_set_group = [[v for v in sorted_notes if v.note_duration.time_position == k] for k, val in itertools.groupby(sorted_notes, lambda x: x.note_duration.time_position)]

      total = len(note_on_set_group)
      for index, group in enumerate(note_on_set_group):
        if index > 0:
          previous_note = note_on_set_group[index-1]
          on_set = Onset(group, previous_note, index+1, total)

        else:
          on_set = Onset(group, None, index+1, total)
        
Main().readXML()





