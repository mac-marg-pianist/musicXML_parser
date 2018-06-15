class Direction(object):
  """Internal representation of a MusicXML Measure's Direction properties.
  
  This represents musical dynamic symbols, expressions with six components:
  1) dynamic               # 'ppp', 'pp', 'p', 'mp' 'mf', 'f', 'ff' 'fff
  2) pedal                 # 'start' or 'stop' or 'change' 'continue' or None
  2) tempo                 # integer
  4) wedge                 # 'crescendo' or 'diminuendo' or 'stop' or None
  5) words                 # string e.g)  Andantino
  6) velocity              # integer

  It parses the standard of the marking point of note.
  """
  def __init__(self, xml_direction, state):
    self.xml_direction = xml_direction
    self.dynamic = None
    self.pedal = None 
    self.tempo = None
    self.wedge_type = None
    self.wedge_status = None
    self.words = None
    self.velocity = None
    self.state = state
    self._parse()
    self._update_wedge()

  def _parse(self):
    """Parse the MusicXML <direction> element."""

    for direction in self.xml_direction:
      self._parse_sound(direction)
      direction_type = direction.find('direction-type')
      child = direction_type.getchildren()[0]
      if child is not None:
        if child.tag == "dynamics":
          self._parse_dynamics(child)
        elif child.tag == "pedal":
          self._parse_pedal(child)
        elif child.tag == "wedge":
          self._parse_wedge(child) 
        elif child.tag == "words":
          self._parse_words(child)
  
  def _parse_pedal(self, xml_pedal):
    """Parse the MusicXML <pedal> element.
    
    Args:
      xml_pedal: XML element with tag type 'pedal'.
    """
    pedal = xml_pedal.attrib['type']
    self.pedal = pedal

  def _parse_sound(self, xml_direction):
    """Parse the MusicXML <sound> element.
    
    Args:
      xml_direction: XML element with tag type 'direction'.
    """
    sound_tag = xml_direction.find('sound')
    if sound_tag is not None:
      attrib = sound_tag.attrib
      if 'dynamics' in attrib:
        self.velocity = attrib['dynamics']
      elif 'tempo' in attrib:
        self.tempo = attrib['tempo']

  def _parse_dynamics(self, xml_dynamics):
    """Parse the MusicXML <dynamics> element.

    Args:
      xml_dynamics: XML element with tag type 'dynamics'.
    """
    dynamic = xml_dynamics.getchildren()[0].tag
    self.dynamic = dynamic

  def _parse_wedge(self, xml_wedge):
    """Parse the MusicXML <wedge> element.
    
    Args:
      xml_wedge: XML element with tag type 'wedge'.
    """
    wedge_type_labels = ['crescendo', 'diminuendo']
    wedge_status_labels = ['start', 'stop', 'continue']
    wedge_type = xml_wedge.attrib['type']
    #print(wedge_type)
    if wedge_type in wedge_type_labels:
      # Add "start" at the point of a wedge starting point
      self.wedge_type = wedge_type
      self.wedge_status = 'start'
    elif wedge_type in wedge_status_labels:
      #self.wedge_type = wedge_type
      self.wedge_status = wedge_type
    #print(self.wedge_type, self.wedge_status, )

    

  def _parse_words(self, xml_words):
    """Parse the MusicXML <words> element.
    
    Args:
      xml_wedge: XML element with tag type 'wedge'.
    """
    self.words = xml_words.text

  def _update_wedge(self):
    # Some MusicXML doesn't have common two voice's wedge value.
    if self.state.previous_note:
      previous_type = self.state.previous_note.direction.wedge_type
      previous_status = self.state.previous_note.direction.wedge_status
      
    #   # Add continue label
      if previous_status == 'start':
        self.wedge_status = 'continue'
        self.wedge_type = previous_type

      # Add continue label
      if previous_status == 'continue':
        if self.wedge_status != 'stop':
          self.wedge_status = 'continue'
          self.wedge_type = previous_type

      if self.wedge_status == 'stop':
        self.wedge_type = previous_type

    pass

